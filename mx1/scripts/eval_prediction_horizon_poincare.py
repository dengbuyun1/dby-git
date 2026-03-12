import argparse
from pathlib import Path
import sys
import numpy as np
import torch
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose.simulator import SimglucoseSBISimulator, SimulatorConfig
from scripts.eval_30_patients import build_posterior
from scripts.evaluate_simglucose import infer_one

def main():
    model_path = ROOT / "results_7dim_50k" / "trained_models" / "npe_simglucose_7d_cnn.pt"
    meta_path = ROOT / "results_7dim_50k" / "simglucose_data" / "meta.pt"
    out_dir = ROOT / "results_7dim_50k" / "pre"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    meta = torch.load(meta_path, map_location="cpu", weights_only=False)
    posterior = build_posterior(str(model_path), meta, device)

    patients = [f"adolescent#{i:03d}" for i in range(1, 11)] + \
               [f"adult#{i:03d}" for i in range(1, 11)] + \
               [f"child#{i:03d}" for i in range(1, 11)]

    # Standard day 1 inference protocol
    train_meals = ((30, 45.0), (300, 70.0), (720, 80.0))
    # Unseen day 2 predictive protocol
    predict_meals = ((90, 60.0), (360, 50.0), (800, 90.0))

    # Prediction horizons in steps (5 min per step)
    # 10=50m, 11=55m, 12=60m, 13=65m
    phs = [10, 11, 12, 13]
    
    # Store errors per patient per PH
    patient_rmse = {ph: [] for ph in phs}
    
    # Store scatter arrays for Poincare plots (True vs Pred) across all patients
    all_true = {ph: [] for ph in phs}
    all_pred = {ph: [] for ph in phs}

    print("开始生成用于 MPC 多步域预测的精度测试与彭加莱图 (Poincare Plot)...")

    for idx, patient_name in enumerate(patients):
        print(f"[{idx+1}/30] 正在提取与测算 {patient_name} 的动态预测误差...")
        
        # 1. Day 1 inference
        obs_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"], meal_schedule=train_meals)
        obs_simulator = SimglucoseSBISimulator(obs_cfg)
        nominal_theta = np.ones(len(meta["parameter_keys"]))
        day1_true_cgm = obs_simulator.simulate(nominal_theta.tolist(), seed=2000 + idx)
        
        samples, log_probs = infer_one(posterior, day1_true_cgm, n_samples=2000, device=device)
        map_est = samples[np.argmax(log_probs)]
        
        # 2. Day 2 true vs twin open loop trajectory
        pred_true_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"], meal_schedule=predict_meals)
        pred_true_simulator = SimglucoseSBISimulator(pred_true_cfg)
        true_cgm2 = pred_true_simulator.simulate(nominal_theta.tolist(), seed=3000 + idx)
        
        pred_twin_cfg = SimulatorConfig(patient_name="adolescent#001", parameter_keys=meta["parameter_keys"], meal_schedule=predict_meals)
        pred_twin_simulator = SimglucoseSBISimulator(pred_twin_cfg)
        twin_cgm2 = pred_twin_simulator.simulate(map_est.tolist(), seed=3000 + idx)
        
        # 3. Simulate rolling MPC prediction with additive disturbance estimator
        # In actual MPC: d(t) = y(t) - y_hat(t). Prediction: y_hat(t+PH|t) = twin(t+PH) + d(t)
        # This isolates the purely structural predictive capability of the ODE!
        
        p_errs = {ph: [] for ph in phs}
        
        for t in range(0, len(true_cgm2) - max(phs)):
            dt = true_cgm2[t] - twin_cgm2[t] # Observer estimation bias correction at current step
            
            for ph in phs:
                pred_val = twin_cgm2[t + ph] + dt
                true_val = true_cgm2[t + ph]
                p_errs[ph].append(true_val - pred_val)
                
                all_true[ph].append(true_val)
                all_pred[ph].append(pred_val)
                
        # Calculate RMSE for this patient
        for ph in phs:
            rmse_val = np.sqrt(np.mean(np.square(p_errs[ph])))
            patient_rmse[ph].append(rmse_val)

    # -------------------
    # Visualization Phase
    # -------------------
    fig = plt.figure(figsize=(18, 16))
    grid = plt.GridSpec(3, 2, hspace=0.4, wspace=0.3)

    # 1. Boxplot of RMSE over horizons
    ax_box = fig.add_subplot(grid[0, :])
    data = []
    labels = []
    avg_rmses = []
    minutes = [ph * 5 for ph in phs]
    for ph, m in zip(phs, minutes):
        data.append(patient_rmse[ph])
        labels.append(f"{m} Min")
        avg_rmses.append(np.mean(patient_rmse[ph]))
    
    ax_box.boxplot(data, tick_labels=labels, widths=0.5, patch_artist=True, boxprops=dict(facecolor="lightblue"))
    ax_box.set_ylabel("RMSE (mg/dL)", fontsize=13)
    ax_box.set_xlabel("Prediction Horizon (预测域)", fontsize=13)
    ax_box.set_title("30名患者: MPC数字孪生不同向前视野(Horizon)的预测精度 RMSE", fontsize=15, fontweight="bold")
    ax_box.grid(alpha=0.3)
    
    for i, avg in enumerate(avg_rmses):
        ax_box.text(i+1, max(data[i]) + 2, f"Avg: {avg:.1f}", ha="center", color="red", fontweight="bold")

    # 2. Poincare Hexbin Density Plots for all 4 horizons
    plot_locs = [(1, 0), (1, 1), (2, 0), (2, 1)]
    cmaps = ["Blues", "Greens", "Oranges", "Reds"]

    for i, (ph, m) in enumerate(zip(phs, minutes)):
        ax = fig.add_subplot(grid[plot_locs[i][0], plot_locs[i][1]])
        t_vals = np.array(all_true[ph])
        p_vals = np.array(all_pred[ph])
        
        # 使用六边形网格密度图 (Hexbin) 替代单调的散点图
        hb = ax.hexbin(t_vals, p_vals, gridsize=40, cmap=cmaps[i], mincnt=1, alpha=0.85)
        cb = fig.colorbar(hb, ax=ax)
        cb.set_label("数据点密度 (Density)", fontsize=10)
        
        # 对角线 (完美预测)
        ax.plot([40, 400], [40, 400], "k--", lw=2, label="完美对角线 (y=x)")
        
        # 绘制 ±20% 安全误差包络区 (类似 Clarke Error Grid 的 A区)
        x_fill = np.linspace(40, 400, 100)
        ax.fill_between(x_fill, x_fill * 0.8, x_fill * 1.2, color='gray', alpha=0.15, label="±20% 临床安全区")
        ax.plot(x_fill, x_fill * 0.8, "gray", linestyle=":", lw=1.5)
        ax.plot(x_fill, x_fill * 1.2, "gray", linestyle=":", lw=1.5)
        
        ax.set_xlim(40, 400)
        ax.set_ylim(40, 400)
        ax.set_xlabel("真实血糖 True CGM (mg/dL)", fontsize=12)
        ax.set_ylabel("预测血糖 Predicted CGM (mg/dL)", fontsize=12)
        ax.set_title(f"向前 {m} 分钟 - 彭加莱密度图\nAvg RMSE: {avg_rmses[i]:.1f}", fontsize=13)
        ax.grid(alpha=0.3)
        if i == 0:
            ax.legend(loc="upper left")

    plot_path = out_dir / "poincare_rmse_horizons_50_to_65.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"\n==================================================")
    print(f"滚动预测与彭加莱密度图生成完毕！")
    for m, avg in zip(minutes, avg_rmses):
        print(f"向前 {m} 分钟预测平均 RMSE: {avg:.2f} mg/dL")
    print(f"图表保存在: {plot_path}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
