# mx13 SBI 改造工作索引

## 1. 目录说明
- `data/`: 初始 18 维高维训练数据与导出 CSV
- `models/`: 初始 18 维模型 `npe_simglucose_highdim.pt`
- `report/`: 初始 18 维评估、配置、计时与本说明
- `figures/`: 初始 18 维示例图
- `logs/`: 初始 18 维训练/评估日志
- `sweeps/`: 维度对比实验（18维、12维、8维）
- `scripts/`: 本轮用于复现实验的脚本

## 2. 脚本说明
- `scripts/train_sbi_variant.py`: 自定义 NPE 训练器，支持 batch/lr/validation 调整
- `scripts/eval_sbi_variant.py`: 统一评估脚本，输出推断与重建汇总
- `scripts/run_sbi_variant.sh`: 单个变体的生成+训练+评估批处理
- `scripts/run_sbi_sweep.sh`: 顺序运行 18维/12维/8维 sweep

## 3. 当前建议结论
- `sweeps/18d_tight_128`: 18维已基本可用，但仍有少量失败样本
- `sweeps/12d_mid_128`: 平均误差最低，是当前最佳精度折中
- `sweeps/8d_core_128`: 稳定性最好，最适合作为默认工程版本

## 4. 关键汇总文件
- `sweeps/18d_tight_128/report/inference_summary.csv`
- `sweeps/18d_tight_128/report/reconstruction_summary.csv`
- `sweeps/12d_mid_128/report/inference_summary.csv`
- `sweeps/12d_mid_128/report/reconstruction_summary.csv`
- `sweeps/8d_core_128/report/inference_summary.csv`
- `sweeps/8d_core_128/report/reconstruction_summary.csv`

