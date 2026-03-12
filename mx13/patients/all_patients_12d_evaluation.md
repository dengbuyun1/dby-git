# 30 患者 12D SBI 总体评估

## 总体结论
- 患者总数: 30
- 平均参数相对误差: 0.0720
- 平均不确定性: 0.0663
- 平均 `real vs virtual` RMSE: 11.1038 mg/dL
- 平均 `real vs nominal` RMSE: 27.3987 mg/dL
- 平均 RMSE 改善率: 46.1434%
- `virtual_better_ratio >= 0.9` 的患者数: 17
- `virtual_better_ratio = 1.0` 的患者数: 6

## 分组统计
- adolescent: n=10, mean_rmse_virtual=11.3017, mean_improve=49.2834%, mean_vbr=0.9115
- adult: n=10, mean_rmse_virtual=14.3640, mean_improve=49.7842%, mean_vbr=0.9423
- child: n=10, mean_rmse_virtual=7.6459, mean_improve=39.3625%, mean_vbr=0.8385

## 最好/最差个体
- 最大平均 RMSE 改善: child#007 (71.5950%)
- 最小平均 RMSE 改善: child#002 (-1.7886%)
- 最低平均重建 RMSE: child#004 (2.8623 mg/dL)
- 最高平均重建 RMSE: child#002 (23.5290 mg/dL)

## 解释
- 若 `mean_improve_rmse_pct > 0`，说明该患者的 12D 虚拟患者平均优于名义患者。
- 若 `virtual_better_ratio` 接近 1，说明该患者在多数测试 case 中稳定优于名义患者。
- `mean_rel_err_all_params` 越低，表示参数恢复更准确；其与 `mean_improve_rmse_pct` 的相关性可用于判断参数误差是否直接映射到轨迹重建效果。
- 参数误差与 RMSE 改善率相关系数: -0.4021
- 不确定性与 RMSE 改善率相关系数: -0.2146

## 输出文件
- `/mnt/f/1_YX/1learn/mx13/patients/all_patients_12d_overall_summary.csv`
- `/mnt/f/1_YX/1learn/mx13/patients/all_patients_12d_group_summary.csv`
- `/mnt/f/1_YX/1learn/mx13/patients/all_patients_12d_rankings.csv`
- `/mnt/f/1_YX/1learn/mx13/patients/all_patients_12d_evaluation.md`