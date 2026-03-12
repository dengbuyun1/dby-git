"""
demo.py
=======
EKF + Smith Predictor 效果演示脚本

使用 simglucose 仿真一天，对比三种控制策略：
  1. 纯 PID（无补偿）
  2. EKF + PID（状态估计，无延迟补偿）
  3. EKF + Smith + PID（完整方案）

输出：
  - results/ekf_smith_demo.png（4张子图）
  - 控制台打印均值血糖、TIR（目标范围时间占比）等指标
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json

# ─── 路径设置 ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))          # 找 simglucose 包

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))   # 找 ekf_glucose / smith_predictor

# ─── 导入模块 ──────────────────────────────────────────────────────────────────
# 安装 gym stub（simglucose 需要）
import types
for mod_name in ["gym", "gym.envs", "gym.envs.registration"]:
    if mod_name not in sys.modules:
        m = types.ModuleType(mod_name)
        if mod_name == "gym.envs.registration":
            m.register = lambda *a, **k: None
        sys.modules[mod_name] = m

from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.actuator.pump import InsulinPump
from simglucose.simulation.env import T1DSimEnv
from simglucose.simulation.scenario import CustomScenario
from simglucose.controller.base import Action

from ekf_glucose import GlucoseEKF
from smith_predictor import DAPSDelayCompensator
from combined_controller import EKFSmithController, SimplePID


# ─── 仿真参数 ──────────────────────────────────────────────────────────────────

PATIENT_NAME   = "adolescent#001"
SENSOR_NAME    = "GuardianRT"
PUMP_NAME      = "Insulet"
SIM_MINUTES    = 1440 * 3   # 3 天
DT             = 5          # 5 min/步
N_STEPS        = SIM_MINUTES // DT
TARGET_BG      = 120.0
START_TIME     = datetime(2025, 1, 1, 6, 0, 0)
# 扩展至3天的进餐计划 (保持每天规律)
MEAL_SCHEDULE  = [
    # Day 1
    (30, 45.0), (300, 70.0), (720, 80.0),
    # Day 2
    (1440 + 30, 45.0), (1440 + 300, 70.0), (1440 + 720, 80.0),
    # Day 3
    (2880 + 30, 45.0), (2880 + 300, 70.0), (2880 + 720, 80.0)
]
SEED           = 42

# 延迟设定（模拟真实场景）
INSULIN_DELAY_MIN = 30      # 胰岛素生理吸收延迟
HW_DELAY_STEPS    = 1       # 硬件/TCP 延迟（1步=5min）


# ─── 构建 simglucose 环境 ──────────────────────────────────────────────────────

def build_env(seed: int):
    patient  = T1DPatient.withName(PATIENT_NAME, seed=seed)
    sensor   = CGMSensor.withName(SENSOR_NAME, seed=seed + 100)
    pump     = InsulinPump.withName(PUMP_NAME)
    scenario_data = [(timedelta(minutes=int(m)), float(g)) for m, g in MEAL_SCHEDULE]
    scenario = CustomScenario(start_time=START_TIME, scenario=scenario_data)
    env = T1DSimEnv(patient=patient, sensor=sensor, pump=pump, scenario=scenario)
    basal = float(patient._params.u2ss * patient._params.BW / 6000.0)  # U/min
    return env, basal * 60.0   # 返回 basal (U/hr)


# ─── 单次仿真 ──────────────────────────────────────────────────────────────────

def run_simulation(
    use_ekf: bool = True,
    use_smith: bool = True,
    kp: float = 0.015,
    ki: float = 0.002,
) -> dict:
    """
    运行一次完整仿真。

    Returns:
        dict with keys: t, bg_real, cgm, G_est, u, cho_events, label
    """
    env, basal_U_hr = build_env(SEED)

    pid = SimplePID(kp=kp, ki=ki, output_min=0.0, output_max=2.0)
    ctrl = EKFSmithController(
        base_controller=pid,
        target_bg=TARGET_BG,
        dt=DT,
        basal_rate=basal_U_hr / 60.0,   # 转回 U/min
        insulin_delay_min=INSULIN_DELAY_MIN,
        hw_delay_steps=HW_DELAY_STEPS,
        use_ekf=use_ekf,
        use_smith=use_smith,
    )

    # 初始重置
    step0 = env.reset()
    if hasattr(step0, "observation"):
        obs0 = step0.observation
    else:
        obs0 = step0[0] if isinstance(step0, tuple) else step0
    cgm0 = float(obs0.CGM) if hasattr(obs0, "CGM") else float(obs0)
    ctrl.initialize(G0=cgm0)

    # 记录
    t_arr    = np.zeros(N_STEPS)
    bg_arr   = np.zeros(N_STEPS)
    cgm_arr  = np.zeros(N_STEPS)
    Gest_arr = np.zeros(N_STEPS)
    u_arr    = np.zeros(N_STEPS)
    cho_arr  = np.zeros(N_STEPS)

    cgm_arr[0]  = cgm0
    Gest_arr[0] = cgm0
    t_arr[0]    = 0

    u = basal_U_hr

    for k in range(1, N_STEPS):
        result = ctrl.step(cgm=cgm_arr[k-1], cho=cho_arr[k-1])
        u = result["insulin"] / (DT / 60.0)   # U → U/hr

        action = Action(basal=u / 60.0, bolus=0.0)  # 转 U/min
        raw = env.step(action)
        if hasattr(raw, "observation"):
            obs, done = raw.observation, raw.done
        else:
            obs, _, done, *_ = raw

        cgm_k = float(obs.CGM) if hasattr(obs, "CGM") else float(obs)
        # 尝试获取真实血糖
        try:
            bg_k = float(env.patient.observation.Gsub)
        except Exception:
            bg_k = cgm_k

        t_arr[k]    = k * DT
        cgm_arr[k]  = max(40.0, min(400.0, cgm_k))
        bg_arr[k]   = max(40.0, min(400.0, bg_k))
        Gest_arr[k] = result["G_est"]
        u_arr[k]    = u

        if done:
            # 填充剩余
            t_arr[k+1:]    = np.arange(k+1, N_STEPS) * DT
            cgm_arr[k+1:]  = cgm_k
            bg_arr[k+1:]   = bg_k
            Gest_arr[k+1:] = cgm_k
            break

    label = f"{'EKF+' if use_ekf else ''}{'Smith+' if use_smith else ''}PID"
    return {
        "t": t_arr / 60.0,    # → hours
        "bg": bg_arr,
        "cgm": cgm_arr,
        "G_est": Gest_arr,
        "u": u_arr,
        "label": label,
    }


# ─── 评估指标 ──────────────────────────────────────────────────────────────────

def metrics(bg_arr: np.ndarray, target: float = 120.0) -> dict:
    tir  = np.mean((bg_arr >= 70) & (bg_arr <= 180)) * 100
    thb  = np.mean(bg_arr < 70) * 100
    thh  = np.mean(bg_arr > 180) * 100
    rmse = float(np.sqrt(np.mean((bg_arr - target) ** 2)))
    return {"TIR%": tir, "Low%": thb, "High%": thh, "RMSE": rmse, "Mean": bg_arr.mean()}


# ─── 绘图 ──────────────────────────────────────────────────────────────────────

def plot_comparison(runs: list[dict], out_path: Path):
    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    colors = ["#e74c3c", "#3498db", "#2ecc71"]

    meal_times = [m / 60.0 for m, g in MEAL_SCHEDULE]

    # ── 子图1：血糖对比 ──────────────────────────────────────────────────────
    ax = axes[0]
    for i, r in enumerate(runs):
        ax.plot(r["t"], r["bg"], lw=2, color=colors[i], label=r["label"])
    ax.axhline(180, color="orange", ls="--", lw=1.2, label="高警戒线 180")
    ax.axhline(70,  color="red",    ls="--", lw=1.2, label="低警戒线  70")
    ax.axhline(TARGET_BG, color="gray", ls=":", lw=1.2, label=f"目标 {TARGET_BG}")
    for mt in meal_times:
        ax.axvline(mt, color="brown", ls=":", lw=1, alpha=0.6)
    ax.set_ylabel("血糖 (mg/dL)", fontsize=11)
    ax.set_ylim(40, 350)
    ax.set_title("血糖控制效果对比（EKF+Smith补偿 vs 基准PID）", fontsize=13)
    ax.legend(fontsize=9, ncol=3)
    ax.grid(alpha=0.3)
    ax.fill_between(runs[0]["t"], 70, 180, alpha=0.05, color="green")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # ── 子图2：EKF 估计效果（以第一个用 EKF 的 run 为例）────────────────────
    ax2 = axes[1]
    for i, r in enumerate(runs):
        ax2.plot(r["t"], r["cgm"], lw=1.5, color=colors[i], alpha=0.5, ls="--", label=f"CGM({r['label']})")
        if "EKF" in r["label"]:
            ax2.plot(r["t"], r["G_est"], lw=2, color=colors[i], label=f"EKF估计({r['label']})")
    ax2.axhline(TARGET_BG, color="gray", ls=":", lw=1)
    ax2.set_ylabel("EKF 状态估计 (mg/dL)", fontsize=11)
    ax2.legend(fontsize=9, ncol=2, frameon=False)
    ax2.grid(alpha=0.3)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── 子图3：胰岛素输注速率 ────────────────────────────────────────────────
    ax3 = axes[2]
    for i, r in enumerate(runs):
        ax3.plot(r["t"], r["u"], lw=1.8, color=colors[i], label=r["label"], alpha=0.85)
    for mt in meal_times:
        ax3.axvline(mt, color="brown", ls=":", lw=1, alpha=0.6, label="进餐" if mt == meal_times[0] else "")
    ax3.set_xlabel("时间 (小时)", fontsize=11)
    ax3.set_ylabel("胰岛素速率 (U/hr)", fontsize=11)
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved: {out_path}")


# ─── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  EKF + Smith Predictor 控制效果演示")
    print(f"  患者: {PATIENT_NAME}  仿真: {SIM_MINUTES} min")
    print("=" * 60)

    print("\n[1/3] 运行基准 PID（无补偿）...")
    run_pid = run_simulation(use_ekf=False, use_smith=False)

    print("[2/3] 运行 EKF + PID（仅状态估计，无延迟补偿）...")
    run_ekf = run_simulation(use_ekf=True, use_smith=False)

    print("[3/3] 运行 EKF + Smith + PID（完整方案）...")
    run_full = run_simulation(use_ekf=True, use_smith=True)

    # 打印指标
    print("\n" + "="*60)
    print(f"{'控制器':<20} {'TIR%':>6} {'Low%':>6} {'High%':>7} {'RMSE':>7} {'Mean BG':>8}")
    print("-"*60)
    for r in [run_pid, run_ekf, run_full]:
        m = metrics(r["bg"])
        print(f"{r['label']:<20} {m['TIR%']:>5.1f}% {m['Low%']:>5.1f}% {m['High%']:>6.1f}% {m['RMSE']:>7.1f} {m['Mean']:>8.1f}")

    # 绘图
    out = ROOT / "results" / "ekfsmith" / "ekf_smith_demo_3days.png"
    plot_comparison([run_pid, run_ekf, run_full], out)

    # 保存 JSON 指标用于自动化报告
    all_metrics = {}
    for r in [run_pid, run_ekf, run_full]:
        all_metrics[r["label"]] = metrics(r["bg"])
    
    with open(ROOT / "results" / "ekfsmith" / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=4)

    print("\nSimulation complete!")
