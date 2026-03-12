from __future__ import annotations

import csv
import math
import statistics as stats
from pathlib import Path

ROOT = Path('/mnt/f/1_YX/1learn/mx13/patients')
IN = ROOT / 'all_patients_12d_summary.csv'
OUT_OVERALL = ROOT / 'all_patients_12d_overall_summary.csv'
OUT_GROUP = ROOT / 'all_patients_12d_group_summary.csv'
OUT_RANK = ROOT / 'all_patients_12d_rankings.csv'
OUT_MD = ROOT / 'all_patients_12d_evaluation.md'


def mean(xs):
    return float(sum(xs) / len(xs)) if xs else float('nan')


def median(xs):
    return float(stats.median(xs)) if xs else float('nan')


def stdev_pop(xs):
    return float(stats.pstdev(xs)) if xs else float('nan')


def corr(xs, ys):
    if not xs or len(xs) != len(ys):
        return float('nan')
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    den = denx * deny
    if den <= 0.0:
        return float('nan')
    return float(num / den)


with IN.open(newline='') as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit('No rows found in aggregate summary')

for row in rows:
    for k, v in list(row.items()):
        if k == 'patient_name':
            continue
        row[k] = float(v)
    name = row['patient_name']
    if name.startswith('adolescent#'):
        row['group'] = 'adolescent'
    elif name.startswith('adult#'):
        row['group'] = 'adult'
    elif name.startswith('child#'):
        row['group'] = 'child'
    else:
        row['group'] = 'unknown'

metric_keys = [
    'mean_rel_err_all_params',
    'mean_uncertainty',
    'mean_rmse_real_vs_virtual',
    'mean_rmse_real_vs_nominal',
    'mean_improve_rmse_pct',
    'virtual_better_ratio',
    'best_improve_rmse_pct',
    'worst_improve_rmse_pct',
]

overall = {'n_patients': len(rows)}
for key in metric_keys:
    vals = [r[key] for r in rows]
    overall[f'{key}_mean'] = mean(vals)
    overall[f'{key}_median'] = median(vals)
    overall[f'{key}_std'] = stdev_pop(vals)

overall['count_virtual_better_ratio_ge_0_8'] = sum(1 for r in rows if r['virtual_better_ratio'] >= 0.8)
overall['count_virtual_better_ratio_ge_0_9'] = sum(1 for r in rows if r['virtual_better_ratio'] >= 0.9)
overall['count_virtual_better_ratio_eq_1_0'] = sum(1 for r in rows if abs(r['virtual_better_ratio'] - 1.0) < 1e-12)
overall['count_positive_mean_improve'] = sum(1 for r in rows if r['mean_improve_rmse_pct'] > 0.0)
overall['corr_param_err_vs_rmse_improve'] = corr(
    [r['mean_rel_err_all_params'] for r in rows],
    [r['mean_improve_rmse_pct'] for r in rows],
)
overall['corr_uncertainty_vs_rmse_improve'] = corr(
    [r['mean_uncertainty'] for r in rows],
    [r['mean_improve_rmse_pct'] for r in rows],
)

with OUT_OVERALL.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(overall.keys()))
    w.writeheader()
    w.writerow(overall)

groups = []
for group_name in ['adolescent', 'adult', 'child']:
    g = [r for r in rows if r['group'] == group_name]
    out = {'group': group_name, 'n_patients': len(g)}
    for key in metric_keys:
        vals = [r[key] for r in g]
        out[f'{key}_mean'] = mean(vals)
        out[f'{key}_median'] = median(vals)
        out[f'{key}_std'] = stdev_pop(vals)
    out['count_virtual_better_ratio_ge_0_9'] = sum(1 for r in g if r['virtual_better_ratio'] >= 0.9)
    out['count_positive_mean_improve'] = sum(1 for r in g if r['mean_improve_rmse_pct'] > 0.0)
    groups.append(out)

with OUT_GROUP.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(groups[0].keys()))
    w.writeheader()
    w.writerows(groups)

best_improve = max(rows, key=lambda r: r['mean_improve_rmse_pct'])
worst_improve = min(rows, key=lambda r: r['mean_improve_rmse_pct'])
best_rmse = min(rows, key=lambda r: r['mean_rmse_real_vs_virtual'])
worst_rmse = max(rows, key=lambda r: r['mean_rmse_real_vs_virtual'])
best_stability = max(rows, key=lambda r: (r['virtual_better_ratio'], r['mean_improve_rmse_pct']))
worst_stability = min(rows, key=lambda r: (r['virtual_better_ratio'], r['mean_improve_rmse_pct']))

rank_rows = [
    {'category': 'best_mean_improve_rmse', 'patient_name': best_improve['patient_name'], 'value': best_improve['mean_improve_rmse_pct']},
    {'category': 'worst_mean_improve_rmse', 'patient_name': worst_improve['patient_name'], 'value': worst_improve['mean_improve_rmse_pct']},
    {'category': 'best_mean_rmse_virtual', 'patient_name': best_rmse['patient_name'], 'value': best_rmse['mean_rmse_real_vs_virtual']},
    {'category': 'worst_mean_rmse_virtual', 'patient_name': worst_rmse['patient_name'], 'value': worst_rmse['mean_rmse_real_vs_virtual']},
    {'category': 'best_stability', 'patient_name': best_stability['patient_name'], 'value': best_stability['virtual_better_ratio']},
    {'category': 'worst_stability', 'patient_name': worst_stability['patient_name'], 'value': worst_stability['virtual_better_ratio']},
]

with OUT_RANK.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['category', 'patient_name', 'value'])
    w.writeheader()
    w.writerows(rank_rows)


def fmt(x):
    if isinstance(x, float) and math.isnan(x):
        return 'nan'
    if isinstance(x, float):
        return f'{x:.4f}'
    return str(x)

lines = []
lines.append('# 30 患者 12D SBI 总体评估')
lines.append('')
lines.append('## 总体结论')
lines.append(f'- 患者总数: {overall["n_patients"]}')
lines.append(f'- 平均参数相对误差: {overall["mean_rel_err_all_params_mean"]:.4f}')
lines.append(f'- 平均不确定性: {overall["mean_uncertainty_mean"]:.4f}')
lines.append(f'- 平均 `real vs virtual` RMSE: {overall["mean_rmse_real_vs_virtual_mean"]:.4f} mg/dL')
lines.append(f'- 平均 `real vs nominal` RMSE: {overall["mean_rmse_real_vs_nominal_mean"]:.4f} mg/dL')
lines.append(f'- 平均 RMSE 改善率: {overall["mean_improve_rmse_pct_mean"]:.4f}%')
lines.append(f'- `virtual_better_ratio >= 0.9` 的患者数: {overall["count_virtual_better_ratio_ge_0_9"]}')
lines.append(f'- `virtual_better_ratio = 1.0` 的患者数: {overall["count_virtual_better_ratio_eq_1_0"]}')
lines.append('')
lines.append('## 分组统计')
for g in groups:
    lines.append(
        f'- {g["group"]}: n={g["n_patients"]}, mean_rmse_virtual={g["mean_rmse_real_vs_virtual_mean"]:.4f}, '
        f'mean_improve={g["mean_improve_rmse_pct_mean"]:.4f}%, mean_vbr={g["virtual_better_ratio_mean"]:.4f}'
    )
lines.append('')
lines.append('## 最好/最差个体')
lines.append(f'- 最大平均 RMSE 改善: {best_improve["patient_name"]} ({best_improve["mean_improve_rmse_pct"]:.4f}%)')
lines.append(f'- 最小平均 RMSE 改善: {worst_improve["patient_name"]} ({worst_improve["mean_improve_rmse_pct"]:.4f}%)')
lines.append(f'- 最低平均重建 RMSE: {best_rmse["patient_name"]} ({best_rmse["mean_rmse_real_vs_virtual"]:.4f} mg/dL)')
lines.append(f'- 最高平均重建 RMSE: {worst_rmse["patient_name"]} ({worst_rmse["mean_rmse_real_vs_virtual"]:.4f} mg/dL)')
lines.append('')
lines.append('## 解释')
lines.append('- 若 `mean_improve_rmse_pct > 0`，说明该患者的 12D 虚拟患者平均优于名义患者。')
lines.append('- 若 `virtual_better_ratio` 接近 1，说明该患者在多数测试 case 中稳定优于名义患者。')
lines.append('- `mean_rel_err_all_params` 越低，表示参数恢复更准确；其与 `mean_improve_rmse_pct` 的相关性可用于判断参数误差是否直接映射到轨迹重建效果。')
lines.append(f'- 参数误差与 RMSE 改善率相关系数: {fmt(overall["corr_param_err_vs_rmse_improve"])}')
lines.append(f'- 不确定性与 RMSE 改善率相关系数: {fmt(overall["corr_uncertainty_vs_rmse_improve"])}')
lines.append('')
lines.append('## 输出文件')
lines.append(f'- `{OUT_OVERALL}`')
lines.append(f'- `{OUT_GROUP}`')
lines.append(f'- `{OUT_RANK}`')
lines.append(f'- `{OUT_MD}`')

OUT_MD.write_text('\n'.join(lines), encoding='utf-8')

print(f'saved: {OUT_OVERALL}')
print(f'saved: {OUT_GROUP}')
print(f'saved: {OUT_RANK}')
print(f'saved: {OUT_MD}')
