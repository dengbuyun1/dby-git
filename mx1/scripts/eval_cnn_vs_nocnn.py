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
from src.sbi_simglucose.pipeline import build_lognormal_multiplier_prior
from scripts.evaluate_simglucose import infer_one, rmse

def build_posterior_cnn(model_path: str, meta: dict, device: torch.device):
    from sbi.inference import NPE
    from sbi.utils.user_input_checks import process_prior
    from src.sbi_simglucose.models import CGMCnnEmbedding
    from sbi.neural_nets import posterior_nn

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    density_estimator = ckpt["density_estimator"]
    
    prior = build_lognormal_multiplier_prior(meta["low"], meta["high"], device=device)
    prior, _, _ = process_prior(prior)

    embedding = CGMCnnEmbedding(output_dim=32).to(device)
    density_estimator_build = posterior_nn(model="maf", embedding_net=embedding)
    
    inference = NPE(prior=prior, density_estimator=density_estimator_build, device=device)
    inference._neural_net = density_estimator
    return inference.build_posterior()

def build_posterior_nocnn(model_path: str, meta: dict, device: torch.device):
    from sbi.inference import NPE
    from sbi.utils.user_input_checks import process_prior
    from sbi.neural_nets import posterior_nn

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    density_estimator = ckpt["density_estimator"]
    
    prior = build_lognormal_multiplier_prior(meta["low"], meta["high"], device=device)
    prior, _, _ = process_prior(prior)

    # 默认无 embedding，直接输入数据到 MAF
    density_estimator_build = posterior_nn(model="maf")
    
    inference = NPE(prior=prior, density_estimator=density_estimator_build, device=device)
    inference._neural_net = density_estimator
    return inference.build_posterior()

def main():
    cnn_model_path = ROOT / "results_7dim_50k" / "trained_models" / "npe_simglucose_7d_cnn.pt"
    nocnn_model_path = ROOT / "results_7dim_50k" / "trained_models" / "npe_simglucose_7d_nocnn.pt"
    meta_path = ROOT / "results_7dim_50k" / "simglucose_data" / "meta.pt"
    
    # Store in the pre directory as requested by the user
    out_dir = ROOT / "results_7dim_50k" / "pre"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    meta = torch.load(meta_path, map_location="cpu", weights_only=False)
    
    print("[1/3] 装载 1D-CNN 特征提取模型...")
    posterior_cnn = build_posterior_cnn(str(cnn_model_path), meta, device)
    print("[2/3] 装载 基础平铺 MLP 无特征模型 (No-CNN)...")
    posterior_nocnn = build_posterior_nocnn(str(nocnn_model_path), meta, device)

    # 选取代表性患者进行画图比较
    selected_patients = ["adolescent#001", "adult#005", "child#005", "child#008", "adult#009"]
    all_patients = [f"adolescent#{i:03d}" for i in range(1, 11)] + \
                   [f"adult#{i:03d}" for i in range(1, 11)] + \
                   [f"child#{i:03d}" for i in range(1, 11)]

    base_cfg = SimulatorConfig(patient_name="adolescent#001", parameter_keys=meta["parameter_keys"])
    base_simulator = SimglucoseSBISimulator(base_cfg)

    cnn_rmses_all = []
    nocnn_rmses_all = []

    # ----------- 对比图绘制 -----------
    fig, axes = plt.subplots(1, 5, figsize=(25, 4), sharex=True)
    axes = axes.flatten()

    print("[3/3] 开始 30 名患者的双模型基准测试 (Zero-Shot 孪生能力)...")
    
    for idx, patient_name in enumerate(all_patients):
        
        target_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"])
        target_simulator = SimglucoseSBISimulator(target_cfg)
        nominal_theta = np.ones(len(meta["parameter_keys"]))
        true_cgm = target_simulator.simulate(nominal_theta.tolist(), seed=1000 + idx)
        
        # --- CNN 推理 ---
        s_cnn, lp_cnn = infer_one(posterior_cnn, true_cgm, n_samples=3000, device=device)
        map_cnn = s_cnn[np.argmax(lp_cnn)]
        cgm_cnn = base_simulator.simulate(map_cnn.tolist(), seed=1000 + idx)
        rmse_cnn = rmse(true_cgm, cgm_cnn)
        cnn_rmses_all.append(rmse_cnn)
        
        # --- No-CNN 推理 ---
        s_nocnn, lp_nocnn = infer_one(posterior_nocnn, true_cgm, n_samples=3000, device=device)
        map_nocnn = s_nocnn[np.argmax(lp_nocnn)]
        cgm_nocnn = base_simulator.simulate(map_nocnn.tolist(), seed=1000 + idx)
        rmse_nocnn = rmse(true_cgm, cgm_nocnn)
        nocnn_rmses_all.append(rmse_nocnn)
        
        print(f"[{idx+1}/30] {patient_name} | RMSE: CNN={rmse_cnn:.2f} vs No-CNN={rmse_nocnn:.2f}")

        # 如果在代表性队列里，画图
        if patient_name in selected_patients:
            ax_idx = selected_patients.index(patient_name)
            ax = axes[ax_idx]
            t_hours = np.arange(len(true_cgm)) * 5 / 60
            
            ax.plot(t_hours, true_cgm, "k-", lw=3, label="True CGM (事实)")
            ax.plot(t_hours, cgm_nocnn, color="coral", lw=2, linestyle="--", label="No-CNN Twin")
            ax.plot(t_hours, cgm_cnn, "b-", lw=2, label="1D-CNN Twin (Our)")
            
            ax.axhline(180, color="orange", ls=":", lw=1)
            ax.axhline(70, color="red", ls=":", lw=1)
            ax.set_title(f"{patient_name}\nCNN: {rmse_cnn:.1f} | No-CNN: {rmse_nocnn:.1f}")
            if ax_idx == 0:
                ax.legend()
            ax.set_ylim(40, 400)
            ax.grid(alpha=0.3)
            ax.set_xlabel("Time (Hours)")

    plt.tight_layout()
    plot_path_curves = out_dir / "cnn_vs_nocnn_curves.png"
    fig.savefig(plot_path_curves, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ----------- 直方图总结 -----------
    fig = plt.figure(figsize=(10, 6))
    
    avg_cnn = np.mean(cnn_rmses_all)
    avg_nocnn = np.mean(nocnn_rmses_all)
    
    x = np.arange(30)
    plt.bar(x - 0.2, cnn_rmses_all, 0.4, label=f"With 1D-CNN (Avg: {avg_cnn:.1f})", color="steelblue")
    plt.bar(x + 0.2, nocnn_rmses_all, 0.4, label=f"No CNN (Avg: {avg_nocnn:.1f})", color="coral")
    plt.axhline(avg_cnn, color="steelblue", linestyle="--", linewidth=1.5)
    plt.axhline(avg_nocnn, color="coral", linestyle="--", linewidth=1.5)
    
    plt.ylabel("重建预测误差 RMSE (mg/dL)")
    plt.title("全部 30 名患者：1D-CNN vs 无特征提取的 SBI 推演质量对比")
    plt.xticks(x, [p.split("#")[0][:2]+p.split("#")[1] for p in all_patients], rotation=90, fontsize=8)
    plt.legend()
    plt.tight_layout()
    
    plot_path_bar = out_dir / "cnn_vs_nocnn_rmse_bar.png"
    fig.savefig(plot_path_bar, dpi=150)
    plt.close(fig)

    print("\n=======================================================")
    print("对比测试已完成！")
    print(f"Average RMSE with 1D-CNN: {avg_cnn:.2f} mg/dL")
    print(f"Average RMSE WITHOUT CNN: {avg_nocnn:.2f} mg/dL")
    print(f"性能提升 (RMSE下降): {(avg_nocnn - avg_cnn) / avg_nocnn * 100:.1f}%")
    print(f"生成对比视图: {plot_path_curves}")
    print(f"生成总表视图: {plot_path_bar}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
