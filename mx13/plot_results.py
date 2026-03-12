"""
mx13 实验数据可视化脚本
类比 SBI_T1D/evaluation.ipynb 中的绘图风格

绘制两类图：
  图1: 参数推断精度总图 (scatter: true vs pred，含误差棒，按所有 test case)
  图2: 指定 patient + case 的 CGM 轨迹图 (真实 vs 用预测参数重建)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─── 配置 ────────────────────────────────────────────────────────────────────

# 要分析的患者目录
PATIENT_DIR = "patients/adult_001/12d_recommended_128"
OUTPUT_DIR  = "figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 参数列表（12维，与 test_theta.csv 列名一致）
PARAM_KEYS = [
    "kabs", "kmax", "kmin",
    "kp1",  "kp2",  "kp3",
    "ka1",  "ka2",  "kd",
    "ksc",  "Vmx",  "Km0",
]

# LaTeX 标签（用于坐标轴）
LATEX_LABELS = {
    "kabs": r"$k_{abs}$",  "kmax": r"$k_{max}$",  "kmin": r"$k_{min}$",
    "kp1":  r"$k_{p1}$",   "kp2":  r"$k_{p2}$",   "kp3":  r"$k_{p3}$",
    "ka1":  r"$k_{a1}$",   "ka2":  r"$k_{a2}$",   "kd":   r"$k_d$",
    "ksc":  r"$k_{sc}$",   "Vmx":  r"$V_{mx}$",   "Km0":  r"$K_{m0}$",
}

# ─── 读取数据 ─────────────────────────────────────────────────────────────────

report = os.path.join(PATIENT_DIR, "report")
inf_pc = pd.read_csv(os.path.join(report, "inference_per_case.csv"))
inf_sum = pd.read_csv(os.path.join(report, "inference_summary.csv"))
traj   = pd.read_csv(os.path.join(report, "all_trajectories.csv"))

print(f"✅ 读取数据完成: {len(inf_pc)} 个 test case, {len(PARAM_KEYS)} 个参数")
print(f"   整体 MARD: {inf_sum['rel_err_mean'].values[0]*100:.2f}%"
      if 'rel_err_mean' in inf_sum.columns else "")

# ─────────────────────────────────────────────────────────────────────────────
# 图1：参数推断精度图（类 SBI_T1D posterior 图风格）
#   - 上三角：每对参数的 true vs pred 散点图
#   - 对角线：单个参数的 true vs pred 散点 + 理想线 y=x
# ─────────────────────────────────────────────────────────────────────────────

n = len(PARAM_KEYS)
fig1, axes = plt.subplots(n, n, figsize=(22, 22))
plt.subplots_adjust(hspace=0.05, wspace=0.05)
fig1.suptitle(f"参数推断精度 — {os.path.basename(PATIENT_DIR.split('/')[1])}",
              fontsize=18, y=0.995)

for i in range(n):
    pk_i = PARAM_KEYS[i]
    true_i = inf_pc[f"true_{pk_i}"].values
    pred_i = inf_pc[f"pred_{pk_i}"].values
    std_i  = inf_pc[f"std_{pk_i}"].values

    for j in range(n):
        ax = axes[i, j]

        # 下三角：关闭
        if j < i:
            ax.axis("off")
            continue

        pk_j = PARAM_KEYS[j]
        true_j = inf_pc[f"true_{pk_j}"].values
        pred_j = inf_pc[f"pred_{pk_j}"].values
        std_j  = inf_pc[f"std_{pk_j}"].values

        if i == j:
            # 对角线：单参数 true vs pred scatter + y=x 参考线
            all_vals = np.concatenate([true_i, pred_i])
            vmin, vmax = all_vals.min() * 0.95, all_vals.max() * 1.05
            ax.plot([vmin, vmax], [vmin, vmax], "k--", lw=1, alpha=0.5)
            ax.errorbar(true_i, pred_i, yerr=std_i,
                        fmt="o", color="steelblue", alpha=0.7,
                        markersize=4, elinewidth=1, capsize=2,
                        label="NPE pred ± std")
            ax.set_xlim(vmin, vmax)
            ax.set_ylim(vmin, vmax)
            ax.set_xlabel(LATEX_LABELS[pk_i], fontsize=14)
            if i == 0:
                ax.legend(fontsize=9, loc="lower right", frameon=False)
        else:
            # 上三角：两参数组合的 true vs pred 散点（对两轴分别）
            ax.scatter(true_j, true_i,  marker="o", s=20,
                       color="black",    alpha=0.6, label="True")
            ax.scatter(pred_j, pred_i,  marker="^", s=20,
                       color="steelblue", alpha=0.6, label="Pred")
            # 误差线（x 方向和 y 方向）
            for k in range(len(true_i)):
                ax.plot([pred_j[k] - std_j[k], pred_j[k] + std_j[k]],
                        [pred_i[k], pred_i[k]],
                        color="steelblue", alpha=0.25, lw=0.8)
                ax.plot([pred_j[k], pred_j[k]],
                        [pred_i[k] - std_i[k], pred_i[k] + std_i[k]],
                        color="steelblue", alpha=0.25, lw=0.8)
            if i == 0 and j == 1:
                ax.legend(fontsize=8, frameon=False, markerscale=1.2)

        ax.set_yticks([])
        ax.set_ylabel("")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=9)
        if i < n - 1:
            ax.set_xticklabels([])

# 添加 y 轴标签（仅对角线行）
for i in range(n):
    axes[i, i].set_ylabel(LATEX_LABELS[PARAM_KEYS[i]], fontsize=11,
                           rotation=0, labelpad=28, va="center")
    axes[i, i].yaxis.set_label_position("right")

fname1 = os.path.join(OUTPUT_DIR, "param_inference_matrix.png")
fig1.savefig(fname1, dpi=150, bbox_inches="tight")
print(f"✅ 图1 保存至: {fname1}")
plt.close(fig1)


# ─────────────────────────────────────────────────────────────────────────────
# 图2：参数相对误差总览条形图（每个参数的 mean ± std，跨所有 case）
# ─────────────────────────────────────────────────────────────────────────────

fig2, ax2 = plt.subplots(figsize=(14, 5))

mean_rel_err = []
std_rel_err  = []
for pk in PARAM_KEYS:
    vals = inf_pc[f"rel_err_{pk}"].values * 100  # 转为 %
    mean_rel_err.append(vals.mean())
    std_rel_err.append(vals.std())

x = np.arange(len(PARAM_KEYS))
bars = ax2.bar(x, mean_rel_err, yerr=std_rel_err,
               color="steelblue", alpha=0.8, capsize=5,
               error_kw=dict(ecolor="black", lw=1.5))

ax2.axhline(10, color="red", ls="--", lw=1.2, label="10% 误差线")
ax2.set_xticks(x)
ax2.set_xticklabels([LATEX_LABELS[pk] for pk in PARAM_KEYS], fontsize=13)
ax2.set_ylabel("相对误差 (%)", fontsize=13)
ax2.set_title(
    f"各参数推断相对误差 — {os.path.basename(PATIENT_DIR.split('/')[1])}\n"
    f"（mean ± std across {len(inf_pc)} test cases）",
    fontsize=13)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.legend(fontsize=11)

# 在每个柱子顶部标注数值
for bar, m, s in zip(bars, mean_rel_err, std_rel_err):
    ax2.text(bar.get_x() + bar.get_width() / 2,
             m + s + 0.3,
             f"{m:.1f}%",
             ha="center", va="bottom", fontsize=9, color="dimgray")

fname2 = os.path.join(OUTPUT_DIR, "param_rel_error_bar.png")
fig2.savefig(fname2, dpi=150, bbox_inches="tight")
print(f"✅ 图2 保存至: {fname2}")
plt.close(fig2)


# ─────────────────────────────────────────────────────────────────────────────
# 图3：CGM 轨迹图（test split 中若干 case 的血糖时间序列）
# ─────────────────────────────────────────────────────────────────────────────

test_traj = traj[traj["split"] == "test"].copy()
test_cases = sorted(test_traj["case"].unique())
n_show = min(6, len(test_cases))  # 最多显示6个 case

fig3, axes3 = plt.subplots(n_show, 1, figsize=(14, 3.5 * n_show), sharex=False)
if n_show == 1:
    axes3 = [axes3]

fig3.suptitle(f"CGM 轨迹 — Test Cases（{os.path.basename(PATIENT_DIR.split('/')[1])}）",
              fontsize=14)

colors = plt.cm.tab10.colors

for idx, case_id in enumerate(test_cases[:n_show]):
    ax = axes3[idx]
    case_data = test_traj[test_traj["case"] == case_id].sort_values("minute")
    minutes = case_data["minute"].values
    cgm     = case_data["cgm"].values

    ax.plot(minutes / 60, cgm, color=colors[idx % 10],
            lw=2, label=f"Case {case_id} — CGM 轨迹")

    # 标注最高/最低血糖
    ax.axhline(180, color="orange", ls="--", lw=1, alpha=0.7, label="高血糖 180")
    ax.axhline(70,  color="red",    ls="--", lw=1, alpha=0.7, label="低血糖 70")

    # 参数误差信息注释
    row = inf_pc[inf_pc["case"] == case_id]
    if not row.empty:
        mard = row["rel_err_mean"].values[0] * 100
        ax.set_title(f"Case {case_id} | 平均相对误差: {mard:.1f}%", fontsize=11)

    ax.set_ylabel("CGM (mg/dL)", fontsize=11)
    ax.set_ylim(40, 400)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=9, loc="upper right", frameon=False)
    ax.grid(alpha=0.3)

axes3[-1].set_xlabel("时间 (小时)", fontsize=12)
plt.tight_layout()

fname3 = os.path.join(OUTPUT_DIR, "cgm_trajectories.png")
fig3.savefig(fname3, dpi=150, bbox_inches="tight")
print(f"✅ 图3 保存至: {fname3}")
plt.close(fig3)


# ─────────────────────────────────────────────────────────────────────────────
# 图4：True vs Pred 散点图（全部案例，所有参数堆叠）
# ─────────────────────────────────────────────────────────────────────────────

fig4, ax4 = plt.subplots(figsize=(7, 7))

all_true, all_pred, all_std = [], [], []
param_colors = plt.cm.tab20.colors

for idx, pk in enumerate(PARAM_KEYS):
    t = inf_pc[f"true_{pk}"].values
    p = inf_pc[f"pred_{pk}"].values
    s = inf_pc[f"std_{pk}"].values
    ax4.errorbar(t, p, yerr=s,
                 fmt="o", markersize=5, alpha=0.7, capsize=2,
                 color=param_colors[idx % 20],
                 label=LATEX_LABELS[pk])
    all_true.extend(t)
    all_pred.extend(p)

vmin = min(all_true + all_pred) * 0.93
vmax = max(all_true + all_pred) * 1.07
ax4.plot([vmin, vmax], [vmin, vmax], "k--", lw=1.2, label="理想 y=x")
ax4.set_xlim(vmin, vmax)
ax4.set_ylim(vmin, vmax)
ax4.set_xlabel("真实值 (normalized)", fontsize=13)
ax4.set_ylabel("预测值 (normalized)", fontsize=13)
ax4.set_title("NPE 参数推断: True vs Predicted（全部参数）", fontsize=13)
ax4.legend(fontsize=8, ncol=2, loc="upper left", frameon=False)
ax4.spines["top"].set_visible(False)
ax4.spines["right"].set_visible(False)
ax4.grid(alpha=0.25)

fname4 = os.path.join(OUTPUT_DIR, "true_vs_pred_all_params.png")
fig4.savefig(fname4, dpi=150, bbox_inches="tight")
print(f"✅ 图4 保存至: {fname4}")
plt.close(fig4)

print("\n🎉 所有图表已生成至 figures/ 目录！")
