import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose import SimglucoseSBISimulator, SimulatorConfig

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def run_sensitivity_scan():
    patient_name = "adolescent#001"
    
    # 我们当前考察的 8 维参数
    param_keys = ["Vmx", "kabs", "kp1", "kp3", "kmax", "p2u", "kp2", "ka2"]
    
    # 我们要在这个范围内扫描每个个体参数（如 0.4x 到 2.5x，分为 10 份）
    scan_scales = np.linspace(0.4, 2.5, 10)
    
    # 定义标准场景：三餐
    meal_schedule = ((30, 45.0), (300, 70.0), (720, 80.0))
    
    cfg = SimulatorConfig(
        patient_name=patient_name,
        sensor_name="GuardianRT",
        pump_name="Insulet",
        sim_minutes=1440,
        seed=42,
        meal_schedule=meal_schedule,
        parameter_keys=param_keys
    )
    
    simulator = SimglucoseSBISimulator(cfg)
    
    # 建立 8 个子图
    fig, axes = plt.subplots(2, 4, figsize=(20, 10), sharex=True, sharey=True)
    axes = axes.flatten()
    
    time_axis = np.arange(288) * 5 / 60  # 转化为小时 (单位：288点 * 5分钟)

    print(f"开始参数敏度独立扫描验证 (Patient: {patient_name})...")
    
    for i, target_param in enumerate(param_keys):
        ax = axes[i]
        
        # 对于当前考核的参数，其他兄弟全部锁定为 1.0 (真实人体基础值)
        print(f"  > 扫描 {target_param}...")
        
        for scale in scan_scales:
            # 基础 nominal = 1.0
            theta_test = np.ones(len(param_keys))
            theta_test[i] = scale  # 只有该参数被扰动
            
            # 由于 batch_simulate 接受 (batch, param_dim) 数组
            theta_test_batch = theta_test.reshape(1, -1)
            
            cgm_res = simulator.batch_simulate(theta_test_batch)
            cgm_curve = cgm_res[0]
            
            # 使用 colormap 区分大小 (深蓝色=小, 亮蓝色/绿色=大)
            color = plt.cm.viridis((scale - 0.4) / (2.5 - 0.4))
            ax.plot(time_axis, cgm_curve, color=color, alpha=0.7, linewidth=1.5)
            
        ax.set_title(f"{target_param} 独立扰动 (0.4x ~ 2.5x)")
        ax.set_xlabel("时间 (小时)")
        ax.set_ylabel("CGM (mg/dL)")
        ax.grid(True, alpha=0.3)
        ax.axhline(60, color='red', linestyle=':', alpha=0.5)
        ax.axhline(180, color='orange', linestyle=':', alpha=0.5)

    plt.suptitle("单参数孤立可辨识性扫略 (Structral Identifiability Check)", fontsize=16)
    plt.tight_layout()
    
    out_dir = ROOT / "results_analysis"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "param_identifiability_scan.png"
    plt.savefig(out_file, dpi=200, bbox_inches='tight')
    print(f"\n✅ 扫描完成。诊断图已保存至: {out_file}")

if __name__ == '__main__':
    run_sensitivity_scan()
