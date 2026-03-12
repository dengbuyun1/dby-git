"""
npe_mpc_controller.py
=====================

基于 SBI (NPE) 数字孪生的模型预测控制器 (MPC) 框架。

架构逻辑：
1. 校准期 (Calibration): 控制器初始化时，接收一段该患者过去 24 小时开环数据（288点）。
2. 数字孪生 (Digital Twin): 控制器后台呼叫预训练的 1D-CNN NPE 模型，瞬间通过 MAP 提取预测出该患者的特征参数 (Theta)。
3. 闭环预测 (Closed-Loop MPC): 在控制阶段，控制器利用上述获得的 Theta，建立高精度的内部 UVA/Padova 模型，
   用于演练评估不同胰岛素输入的未来 1 小时响应，选择最优的 basal/bolus 输出。

符合 simglucose 的 Controller 标准格式。
"""

import numpy as np
import torch
import warnings
from simglucose.controller.base import Controller, Action
from pathlib import ROOT

# 假设我们在 mx1 路径下
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

class NPEMPCController(Controller):
    def __init__(
        self, 
        init_state, 
        npe_model_path: str, 
        meta_path: str, 
        history_cgm: np.ndarray, 
        base_patient: str = "adolescent#001",
        target_bg: float = 120.0,
        prediction_horizon_steps: int = 12  # 预测域 60 分钟 (12 * 5min)
    ):
        """
        Args:
            init_state: simglucose 控制器标准参数
            npe_model_path: 训练好的 npe_simglucose_7d_cnn.pt 路径
            meta_path: 参数元数据 meta.pt 路径
            history_cgm: 该名患者的 24小时 (288长) 历史开环 CGM 数据
            base_patient: 借用的 UVA/Padova 底层结构人选
            target_bg: MPC 想要维持的目标血糖
        """
        super().__init__(init_state)
        self.target_bg = target_bg
        self.prediction_horizon = prediction_horizon_steps
        self.base_patient = base_patient
        
        # 1. 初始化并唤醒数字孪生神探
        print(f"\n[NPE-MPC] 正在初始化控制器，开始构建 {base_patient} 的数字孪生...")
        self.digital_twin_theta = self._extract_digital_twin_map(
            npe_model_path, meta_path, history_cgm
        )
        print(f"[NPE-MPC] 孪生参数提取成功: {np.round(self.digital_twin_theta, 3)}")

    def _extract_digital_twin_map(self, model_path, meta_path, history_cgm):
        """调用 NPE 提取 MAP (最大后验概率) 参数估算"""
        from scripts.eval_30_patients import build_posterior
        from scripts.evaluate_simglucose import infer_one
        
        device = torch.device("cpu")
        meta = torch.load(meta_path, map_location=device, weights_only=False)
        posterior = build_posterior(model_path, meta, device)
        
        # NPE 瞬间推断
        samples, log_probs = infer_one(posterior, history_cgm, n_samples=3000, device=device)
        best_idx = np.argmax(log_probs)
        map_theta = samples[best_idx]
        return map_theta

    def policy(self, observation, reward, done, **info):
        """
        simglucose 控制器的核心计算每步 (5 min) 的注射量。
        在真正的 MPC 中，这里会使用 self.digital_twin_theta 去正向模拟未来。
        """
        cgm = observation.CGM
        
        # TODO: 接入 SciPy Optimize 或者 Scenario-based 候选采样
        # 这里为示例代码，展示了 MPC 将如何在内部模拟
        # 
        # 伪代码：
        # candidates_u = [0.0, 0.02, 0.05, 0.1, 0.2] # 不同的基础率 U/min
        # best_u = 0.0
        # min_cost = float('inf')
        # 
        # for u in candidates_u:
        #     # 利用我们的精准数字孪生参数，推演未来 12 步 (1小时)
        #     simulated_future_cgm_trajectory = simulate_uva_padova(
        #          self.base_patient, self.digital_twin_theta, current_ODE_state, horizon=12, insulin_in=u
        #     )
        #     
        #     # 成本函数：偏离靶点 120 的差值的平方和，低血糖给极大量惩罚
        #     cost = np.sum((simulated_future_cgm_trajectory - self.target_bg)**2)
        #     if np.min(simulated_future_cgm_trajectory) < 70:
        #         cost += 999999.0 # 低血糖致死惩罚
        #         
        #     if cost < min_cost:
        #         min_cost = cost
        #         best_u = u

        # 为了保证程序正常运行能编译，直接输出一个平滑 PI 启发试算出的量：
        error = cgm - self.target_bg
        if cgm < 80:
            basal_opt = 0.0  # 切断胰岛素 (低血糖保护)
        else:
            basal_opt = 0.03 + 0.001 * error  # 模拟 MPC 解算出来的速率 U/min
            
        basal_opt = max(0.0, min(basal_opt, 0.1)) # 限制最大胰岛素
        
        # info["patient_name"] 可获取环境传递的信息
        return Action(basal=basal_opt, bolus=0.0)

    def reset(self):
        """
        Reset controller state.
        """
        self.state = self.init_state
