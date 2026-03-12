# 30 患者批处理说明（mx13）

## 1. 运行脚本
- `scripts/run_sbi_all_patients_12d.sh`

该脚本会按以下患者顺序，逐个运行 12 维推荐方案：
- 10 名青少年
- 10 名成人
- 10 名儿童

## 2. 单患者结果路径
每个患者结果保存在：
- `mx13/patients/<patient_safe>/12d_recommended_128/`

例如：
- `mx13/patients/adolescent_001/12d_recommended_128/`
- `mx13/patients/adult_003/12d_recommended_128/`
- `mx13/patients/child_010/12d_recommended_128/`

其中包含：
- `data/`: 训练与测试数据
- `models/`: 训练后的模型
- `report/`: 推断与重建汇总
- `logs/`: 生成、训练、评估日志

## 3. 运行状态
批处理进度文件：
- `mx13/patients/_batch_status_12d.txt`

## 4. 汇总
全部患者完成后，可运行：
- `python mx13/scripts/aggregate_patient_results.py`

汇总文件输出到：
- `mx13/patients/all_patients_12d_summary.csv`
