"""
mx13 结果诊断脚本
系统性检查：NPE 是否真的学到了有效的参数区分能力，还是只是预测均值(~1.0)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

# ─── 路径配置 ─────────────────────────────────────────────────────────────────
PATIENT_DIR = "patients/adult_001/12d_recommended_128"
OUTPUT_DIR  = "figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PARAM_KEYS = ["kabs","kmax","kmin","kp1","kp2","kp3","ka1","ka2","kd","ksc","Vmx","Km0"]
LATEX = {"kabs":r"$k_{abs}$","kmax":r"$k_{max}$","kmin":r"$k_{min}$",
         "kp1":r"$k_{p1}$","kp2":r"$k_{p2}$","kp3":r"$k_{p3}$",
         "ka1":r"$k_{a1}$","ka2":r"$k_{a2}$","kd":r"$k_d$",
         "ksc":r"$k_{sc}$","Vmx":r"$V_{mx}$","Km0":r"$K_{m0}$"}

# ─── 读取数据 ─────────────────────────────────────────────────────────────────
report  = os.path.join(PATIENT_DIR, "report")
inf_pc  = pd.read_csv(os.path.join(report, "inference_per_case.csv"))
rec_pc  = pd.read_csv(os.path.join(report, "reconstruction_per_case.csv"))
inf_sum = pd.read_csv(os.path.join(report, "inference_summary.csv"))
meta_txt = open(os.path.join(report, "run_metadata.txt")).read()

# ─────────────────────────────────────────────────────────────────────────────
# 诊断1: NPE 是否只预测均值(1.0)？
# 比较 true 值的分散度 vs pred 值的分散度
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("【诊断1】：NPE 预测值与真实值的分布对比")
print("=" * 60)
print(f"{'参数':<8} {'真值范围':>18} {'预测范围':>18} {'真值std':>10} {'预测std':>10} {'相关系数r':>10}")
print("-" * 80)
for pk in PARAM_KEYS:
    tv = inf_pc[f"true_{pk}"].values
    pv = inf_pc[f"pred_{pk}"].values
    r  = np.corrcoef(tv, pv)[0, 1]
    print(f"{pk:<8} [{tv.min():.3f}, {tv.max():.3f}]  [{pv.min():.3f}, {pv.max():.3f}]"
          f"  {tv.std():>10.4f}  {pv.std():>10.4f}  {r:>10.4f}")

print()
print("【诊断2】：重建质量 vs 名义模型（nominal=全1参数）")
print("=" * 60)
print(f"  虚拟患者 MARD: {rec_pc['mard_real_vs_virtual_pct'].mean():.2f}%（越低越好）")
print(f"  名义模型 MARD: {rec_pc['mard_real_vs_nominal_pct'].mean():.2f}%（基线）")
better = (rec_pc["virtual_better_than_nominal"] == 1.0).sum()
print(f"  虚拟优于名义: {better}/{len(rec_pc)} ({100*better/len(rec_pc):.1f}%)")
print(f"  平均 RMSE 改善: {rec_pc['improve_rmse_pct'].mean():.1f}%")

print()
print("【诊断3】：训练数据量检查")
print(f"  从 run_metadata.txt: num_samples={128}")
print(f"  test cases: {len(inf_pc)}")

# ─────────────────────────────────────────────────────────────────────────────
# 核心诊断图：True vs Pred（每个参数一行）
# 加了 y=x 线和 y=1 基线，直观看 NPE 是否在追踪真实值
# ─────────────────────────────────────────────────────────────────────────────
n = len(PARAM_KEYS)
fig, axes = plt.subplots(3, 4, figsize=(16, 12))
axes = axes.flatten()
fig.suptitle("诊断图：NPE True vs Predicted（每参数）\n"
             "若预测值与真值无相关，点会横成一条水平线（回归均值）",
             fontsize=13)

for idx, pk in enumerate(PARAM_KEYS):
    ax = axes[idx]
    tv = inf_pc[f"true_{pk}"].values
    pv = inf_pc[f"pred_{pk}"].values
    sv = inf_pc[f"std_{pk}"].values

    # 散点 + 误差棒
    ax.errorbar(tv, pv, yerr=sv, fmt='o', color='steelblue',
                alpha=0.7, ms=5, elinewidth=1, capsize=3)

    # y=x 理想线
    lims = [min(tv.min(), pv.min()) * 0.96, max(tv.max(), pv.max()) * 1.04]
    ax.plot(lims, lims, 'r--', lw=1.5, label='y=x (理想)')

    # y=1 基线（名义模型就是预测1）
    ax.axhline(1.0, color='gray', ls=':', lw=1, label='y=1 (名义)')

    # 相关系数
    r = np.corrcoef(tv, pv)[0, 1]
    ax.set_title(f"{LATEX[pk]}   r={r:.3f}", fontsize=12)
    ax.set_xlabel("True value", fontsize=9)
    ax.set_ylabel("Predicted", fontsize=9)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout()
diag1_path = os.path.join(OUTPUT_DIR, "diag_true_vs_pred_per_param.png")
fig.savefig(diag1_path, dpi=150, bbox_inches='tight')
print(f"\n✅ 诊断图1 保存: {diag1_path}")
plt.close(fig)

# ─────────────────────────────────────────────────────────────────────────────
# 诊断图2：重建质量对比（真实患者 vs 虚拟患者 vs 名义患者 的 MARD 对比）
# ─────────────────────────────────────────────────────────────────────────────
fig2, (ax_bar, ax_scatter) = plt.subplots(1, 2, figsize=(14, 5))
fig2.suptitle("重建质量诊断：虚拟患者 vs 名义患者", fontsize=13)

# 左：每个 case 的 MARD 对比（条形图）
cases = rec_pc['case'].values
x = np.arange(len(cases))
w = 0.35
b1 = ax_bar.bar(x - w/2, rec_pc['mard_real_vs_virtual_pct'], w,
                 color='steelblue', alpha=0.8, label='虚拟患者（NPE推断）')
b2 = ax_bar.bar(x + w/2, rec_pc['mard_real_vs_nominal_pct'], w,
                 color='salmon', alpha=0.8, label='名义患者（全参数=1）')
ax_bar.set_xticks(x)
ax_bar.set_xticklabels([str(c) for c in cases], fontsize=7)
ax_bar.set_xlabel("Test Case", fontsize=11)
ax_bar.set_ylabel("MARD (%)", fontsize=11)
ax_bar.set_title("各 Case 的血糖重建 MARD", fontsize=11)
ax_bar.legend(fontsize=9, frameon=False)
ax_bar.spines['top'].set_visible(False)
ax_bar.spines['right'].set_visible(False)
ax_bar.grid(axis='y', alpha=0.3)

# 右：改善率分布（直方图）
improve = rec_pc['improve_rmse_pct'].values
colors_hist = ['steelblue' if v >= 0 else 'salmon' for v in improve]
ax_scatter.bar(range(len(improve)), improve, color=colors_hist, alpha=0.8)
ax_scatter.axhline(0, color='black', lw=1)
mean_imp = improve.mean()
ax_scatter.axhline(mean_imp, color='red', ls='--', lw=1.5,
                    label=f'均值 = {mean_imp:.1f}%')
ax_scatter.set_xlabel("Test Case", fontsize=11)
ax_scatter.set_ylabel("RMSE 改善率 (%)\n正值=虚拟优于名义", fontsize=11)
ax_scatter.set_title("NPE 虚拟患者相对名义患者的 RMSE 改善率", fontsize=11)
ax_scatter.legend(fontsize=9, frameon=False)
ax_scatter.spines['top'].set_visible(False)
ax_scatter.spines['right'].set_visible(False)
ax_scatter.grid(axis='y', alpha=0.3)

plt.tight_layout()
diag2_path = os.path.join(OUTPUT_DIR, "diag_reconstruction_quality.png")
fig2.savefig(diag2_path, dpi=150, bbox_inches='tight')
print(f"✅ 诊断图2 保存: {diag2_path}")
plt.close(fig2)

# ─────────────────────────────────────────────────────────────────────────────
# 诊断图3：参数推断偏差分析（pred - true）
# 看 NPE 是否系统性地往 1.0 方向偏移（识别 shrinkage 效应）
# ─────────────────────────────────────────────────────────────────────────────
fig3, axes3 = plt.subplots(3, 4, figsize=(16, 11))
axes3 = axes3.flatten()
fig3.suptitle("偏差诊断：(pred - true) vs true\n"
              "理想情况：随机分布在 y=0 两侧\n"
              "若右上/左下集中 → 均值收缩（回归均值偏差）",
              fontsize=12)

for idx, pk in enumerate(PARAM_KEYS):
    ax = axes3[idx]
    tv = inf_pc[f"true_{pk}"].values
    pv = inf_pc[f"pred_{pk}"].values
    bias = pv - tv

    # 颜色：偏低用红色，偏高用蓝色
    colors_pt = ['steelblue' if b >= 0 else 'salmon' for b in bias]
    ax.scatter(tv, bias, c=colors_pt, s=30, alpha=0.8)
    ax.axhline(0, color='black', lw=1)
    ax.axhline(np.mean(bias), color='red', ls='--', lw=1,
               label=f'mean bias = {np.mean(bias):.3f}')

    # 标注：若 true < 1，bias > 0 就是向 1.0 收缩
    ax.axvline(1.0, color='gray', ls=':', lw=0.8)

    r = np.corrcoef(tv, bias)[0, 1]
    ax.set_title(f"{LATEX[pk]}   bias-r={r:.3f}", fontsize=11)
    ax.set_xlabel("True value", fontsize=9)
    ax.set_ylabel("Pred - True", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout()
diag3_path = os.path.join(OUTPUT_DIR, "diag_bias_analysis.png")
fig3.savefig(diag3_path, dpi=150, bbox_inches='tight')
print(f"✅ 诊断图3 保存: {diag3_path}")
plt.close(fig3)

print("\n🎉 诊断完成！请查看 figures/ 中的3张诊断图")
print("\n若 diag_true_vs_pred_per_param.png 中各参数 r 值接近0，")
print("说明 NPE 没有学到区分能力（只预测均值）。")
print("若 diag_bias_analysis.png 中 bias 与 true 呈负相关，")
print("说明存在均值收缩效应（这是小样本 SBI 的常见问题）。")
