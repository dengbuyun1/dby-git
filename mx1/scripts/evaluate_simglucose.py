"""
evaluate_simglucose.py
=========================
评估 NPE 模型在 simglucose 上的参数推断效果，并绘制可视化图表。

对应 SBI_T1D 的 evaluation.ipynb，但以脚本形式运行。

输出图表（保存至 --figure-dir）：
  1. true_vs_pred_per_param.png  — 每个参数的 True vs Predicted 散点
  2. param_rel_error_bar.png     — 各参数平均相对误差条形图
  3. bias_analysis.png           — 偏差 (pred-true) vs true 图
  4. cgm_reconstruction.png     — CGM 轨迹：真实 / 虚拟 / 名义
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose import SimglucoseSBISimulator, SimulatorConfig
from src.sbi_simglucose.pipeline import build_lognormal_multiplier_prior


# ─── 评估核心逻辑 ─────────────────────────────────────────────────────────────

def build_posterior(model_path: str, meta: dict, device: torch.device):
    """从保存的 density_estimator 重建 posterior。"""
    from sbi.inference import NPE
    from sbi.utils.user_input_checks import process_prior

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(ckpt, dict) and "density_estimator" in ckpt:
        density_estimator = ckpt["density_estimator"]
    else:
        density_estimator = ckpt

    low = meta["low"]
    high = meta["high"]
    prior = build_lognormal_multiplier_prior(low=low, high=high, device=device)
    prior, _, _ = process_prior(prior)
    inference = NPE(prior=prior, device=device)
    posterior = inference.build_posterior(density_estimator)
    return posterior


def infer_one(posterior, x_obs: np.ndarray, n_samples: int, device: torch.device) -> np.ndarray:
    """对单个观测 x 采样后验，返回 (n_samples, n_params) array。"""
    x_t = torch.from_numpy(x_obs.astype(np.float32)).to(device)
    with torch.no_grad():
        samples = posterior.sample((n_samples,), x=x_t, show_progress_bars=False)
        log_probs = posterior.log_prob(samples, x=x_t)
    return samples.cpu().numpy(), log_probs.cpu().numpy()


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mard(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.maximum(np.abs(a), 1e-6)
    return float(np.mean(np.abs(b - a) / denom) * 100.0)


# ─── 绘图函数 ─────────────────────────────────────────────────────────────────

LATEX = {
    "kabs": r"$k_{abs}$", "kmax": r"$k_{max}$", "kmin": r"$k_{min}$",
    "kp1":  r"$k_{p1}$",  "kp2":  r"$k_{p2}$",  "kp3":  r"$k_{p3}$",
    "ka1":  r"$k_{a1}$",  "ka2":  r"$k_{a2}$",  "kd":   r"$k_d$",
    "ksc":  r"$k_{sc}$",  "Vmx":  r"$V_{mx}$",  "Km0":  r"$K_{m0}$",
}

def label(k: str) -> str:
    return LATEX.get(k, k)


def plot_true_vs_pred(param_keys, true_np, pred_mean, pred_std, out_path: Path, patient_name: str):
    n = len(param_keys)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    if n == 1:
        axes = np.array([[axes]])
    axes = np.array(axes).reshape(nrows, ncols)

    for idx, pk in enumerate(param_keys):
        ax = axes[idx // ncols][idx % ncols]
        tv = true_np[:, idx]
        pv = pred_mean[:, idx]
        sv = pred_std[:, idx]

        lims = [min(tv.min(), pv.min()) * 0.95, max(tv.max(), pv.max()) * 1.05]
        ax.plot(lims, lims, "r--", lw=1.5, label="y=x")
        ax.axhline(1.0, color="gray", ls=":", lw=1, label="y=1 (名义)")
        ax.errorbar(tv, pv, yerr=sv, fmt="o", color="steelblue",
                    alpha=0.7, ms=5, elinewidth=1, capsize=3)
        r = float(np.corrcoef(tv, pv)[0, 1]) if len(tv) > 1 else 0.0
        ax.set_title(f"{label(pk)}  r={r:.3f}", fontsize=12)
        ax.set_xlabel("True scale", fontsize=9)
        ax.set_ylabel("Pred scale", fontsize=9)
        ax.set_xlim(lims); ax.set_ylim(lims)
        ax.legend(fontsize=7, frameon=False)
        ax.grid(alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # 隐藏多余格
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    fig.suptitle(f"NPE True vs Predicted — {patient_name}", fontsize=13)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ 图1 保存: {out_path}")


def plot_rel_error_bar(param_keys, rel_errs_pct: np.ndarray, out_path: Path, patient_name: str, n_cases: int):
    """rel_errs_pct: (n_cases, n_params) 相对误差百分比数组。"""
    mean_err = rel_errs_pct.mean(axis=0)
    std_err  = rel_errs_pct.std(axis=0)

    fig, ax = plt.subplots(figsize=(max(8, len(param_keys) * 1.2), 5))
    x = np.arange(len(param_keys))
    bars = ax.bar(x, mean_err, yerr=std_err, color="steelblue", alpha=0.8,
                  capsize=5, error_kw=dict(ecolor="black", lw=1.5))
    ax.axhline(10, color="red", ls="--", lw=1.2, label="10% 误差线")
    ax.set_xticks(x)
    ax.set_xticklabels([label(pk) for pk in param_keys], fontsize=12)
    ax.set_ylabel("相对误差 (%)", fontsize=12)
    ax.set_title(f"参数推断相对误差 — {patient_name} ({n_cases} cases)", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=10)
    for bar, m, s in zip(bars, mean_err, std_err):
        ax.text(bar.get_x() + bar.get_width() / 2, m + s + 0.3,
                f"{m:.1f}%", ha="center", va="bottom", fontsize=9, color="dimgray")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ 图2 保存: {out_path}")


def plot_bias(param_keys, true_np, pred_mean, out_path: Path, patient_name: str):
    n = len(param_keys)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = np.array(axes).reshape(nrows, ncols)

    for idx, pk in enumerate(param_keys):
        ax = axes[idx // ncols][idx % ncols]
        tv = true_np[:, idx]
        bias = pred_mean[:, idx] - tv
        colors = ["steelblue" if b >= 0 else "salmon" for b in bias]
        ax.scatter(tv, bias, c=colors, s=30, alpha=0.8)
        ax.axhline(0, color="black", lw=1)
        ax.axhline(float(bias.mean()), color="red", ls="--", lw=1,
                   label=f"mean={bias.mean():.3f}")
        ax.axvline(1.0, color="gray", ls=":", lw=0.8)
        bias_r = float(np.corrcoef(tv, bias)[0, 1]) if len(tv) > 1 else 0.0
        ax.set_title(f"{label(pk)}  bias-r={bias_r:.3f}", fontsize=12)
        ax.set_xlabel("True scale", fontsize=9)
        ax.set_ylabel("Pred - True", fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        ax.grid(alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    fig.suptitle(f"偏差分析 (Pred-True) vs True — {patient_name}\n"
                 "若 bias-r ≈ -1 → 预测值向均值(1.0)收缩", fontsize=12)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ 图3 保存: {out_path}")


def plot_cgm_reconstruction(
    param_keys, meta, test_theta_np, pred_mean_np, n_show, simulator_cfg, out_path: Path
):
    """用真实 theta / 预测 mean theta / 全1名义 theta 重建 CGM，对比绘图。"""
    simulator = SimglucoseSBISimulator(simulator_cfg)
    n_show = min(n_show, len(test_theta_np))

    fig, axes = plt.subplots(n_show, 1, figsize=(14, 3.5 * n_show), sharex=False)
    if n_show == 1:
        axes = [axes]

    for i in range(n_show):
        ax = axes[i]
        theta_true = test_theta_np[i]
        theta_pred = pred_mean_np[i]
        theta_nom  = np.ones_like(theta_true)
        seed_i = 800000 + i

        cgm_real = simulator.simulate(theta_true.tolist(), seed=seed_i)
        cgm_virt = simulator.simulate(theta_pred.tolist(), seed=seed_i)
        cgm_nom  = simulator.simulate(theta_nom.tolist(),  seed=seed_i)

        t_min = np.arange(len(cgm_real)) * 5  # 5分钟步长
        ax.plot(t_min / 60, cgm_real, "k-",   lw=2,   label="真实患者")
        ax.plot(t_min / 60, cgm_virt, "b--",  lw=1.5, label="NPE虚拟患者")
        ax.plot(t_min / 60, cgm_nom,  "r:",   lw=1.2, label="名义患者(=1)")

        ax.axhline(180, color="orange", ls="--", lw=0.8, alpha=0.6)
        ax.axhline(70,  color="red",    ls="--", lw=0.8, alpha=0.6)

        rmse_virt = rmse(cgm_real, cgm_virt)
        rmse_nom  = rmse(cgm_real, cgm_nom)
        improve   = 100 * (1 - rmse_virt / max(rmse_nom, 1e-6))
        ax.set_title(
            f"案例 {i}  |  RMSE 虚拟={rmse_virt:.1f}  名义={rmse_nom:.1f}  改善={improve:.1f}%",
            fontsize=11
        )
        ax.set_ylabel("CGM (mg/dL)", fontsize=10)
        ax.set_ylim(40, 400)
        ax.legend(fontsize=9, loc="upper right", frameon=False)
        ax.grid(alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[-1].set_xlabel("时间 (小时)", fontsize=11)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ 图4 保存: {out_path}")


# ─── 主流程 ───────────────────────────────────────────────────────────────────

def main(args):
    device = torch.device("cpu")

    # 加载数据
    test_theta, test_x = torch.load(args.test_data, map_location="cpu", weights_only=False)
    meta = torch.load(args.meta, map_location="cpu", weights_only=False)

    param_keys = tuple(str(k) for k in meta["parameter_keys"])
    n_params = len(param_keys)
    n_cases = len(test_theta)
    print(f"\n✅ 加载完毕: {n_cases} 个测试案例, {n_params} 个参数: {param_keys}")
    print(f"   x 维度: {test_x.shape[1]}")

    # 构建后验
    posterior = build_posterior(args.model_path, meta, device)

    # 对每个测试案例推断
    test_theta_np = test_theta.numpy()   # (n_cases, n_params)
    test_x_np     = test_x.numpy()       # (n_cases, T)

    pred_mean_list, pred_std_list, rel_errs_list = [], [], []
    pred_map_list = []

    for i in range(n_cases):
        if i % 10 == 0:
            print(f"  推断 case {i}/{n_cases}...")
        samples, log_probs = infer_one(posterior, test_x_np[i], n_samples=args.posterior_samples, device=device)
        best_idx = np.argmax(log_probs)
        map_est = samples[best_idx]
        
        # samples: (n_samples, n_params)
        pm = samples.mean(axis=0)   # (n_params,)
        ps = samples.std(axis=0)    # (n_params,)
        tv = test_theta_np[i]       # (n_params,)
        re = np.abs(pm - tv) / np.maximum(np.abs(tv), 1e-9) * 100  # %

        pred_mean_list.append(pm)
        pred_std_list.append(ps)
        rel_errs_list.append(re)
        pred_map_list.append(map_est)

    pred_mean_np = np.stack(pred_mean_list)   # (n_cases, n_params)
    pred_map_np  = np.stack(pred_map_list)    # (n_cases, n_params)
    pred_std_np  = np.stack(pred_std_list)
    rel_errs_np  = np.stack(rel_errs_list)

    # 汇总统计
    print("\n" + "="*60)
    print("  参数推断误差汇总（相对误差 %）")
    print("="*60)
    print(f"{'参数':<8} {'mean%':>8} {'std%':>8} {'r':>8}")
    print("-"*40)
    for j, pk in enumerate(param_keys):
        tv_col = test_theta_np[:, j]
        pm_col = pred_mean_np[:, j]
        r = float(np.corrcoef(tv_col, pm_col)[0, 1]) if n_cases > 1 else 0.0
        print(f"{pk:<8} {rel_errs_np[:, j].mean():>8.2f} {rel_errs_np[:, j].std():>8.2f} {r:>8.3f}")
    print(f"\n  整体平均相对误差: {rel_errs_np.mean():.2f}%")

    # 绘图
    fig_dir = Path(args.figure_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    patient_name = str(meta.get("patient_name", "unknown"))

    plot_true_vs_pred(
        param_keys, test_theta_np, pred_mean_np, pred_std_np,
        out_path=fig_dir / "true_vs_pred_per_param.png",
        patient_name=patient_name,
    )
    plot_rel_error_bar(
        param_keys, rel_errs_np,
        out_path=fig_dir / "param_rel_error_bar.png",
        patient_name=patient_name, n_cases=n_cases,
    )
    plot_bias(
        param_keys, test_theta_np, pred_mean_np,
        out_path=fig_dir / "bias_analysis.png",
        patient_name=patient_name,
    )

    # CGM 重建图（用仿真器重跑）
    if not args.skip_reconstruction:
        meal_schedule = tuple(
            (int(m), float(g)) for m, g in meta.get("meal_schedule", ((30, 45.0), (300, 70.0), (720, 80.0)))
        )
        sim_cfg = SimulatorConfig(
            patient_name=patient_name,
            sensor_name=str(meta.get("sensor_name", "GuardianRT")),
            pump_name=str(meta.get("pump_name", "Insulet")),
            sim_minutes=int(meta.get("sim_minutes", 1440)),
            seed=42,
            meal_schedule=meal_schedule,
            parameter_keys=param_keys,
        )
        plot_cgm_reconstruction(
            param_keys, meta, test_theta_np, pred_map_np,
            n_show=args.n_cgm_show,
            simulator_cfg=sim_cfg,
            out_path=fig_dir / "cgm_reconstruction.png",
        )

    print(f"\n🎉 所有图表保存至: {fig_dir}")


# ─── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    default_data = ROOT / "results" / "simglucose_data"
    default_model = ROOT / "trained_models" / "npe_simglucose.pt"

    parser = argparse.ArgumentParser(description="评估 NPE simglucose 模型并绘制图表")
    parser.add_argument("--test-data",   type=str, default=str(default_data / "test_data.pt"))
    parser.add_argument("--meta",        type=str, default=str(default_data / "meta.pt"))
    parser.add_argument("--model-path",  type=str, default=str(default_model))
    parser.add_argument("--figure-dir",  type=str, default=str(ROOT / "results" / "figures"))
    parser.add_argument("--posterior-samples", type=int, default=256)
    parser.add_argument("--n-cgm-show",  type=int, default=4,
                        help="CGM 重建图中展示的案例数")
    parser.add_argument("--skip-reconstruction", action="store_true",
                        help="跳过耗时的 CGM 重建仿真（仅出参数误差图）")
    main(parser.parse_args())
