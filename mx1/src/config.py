from dataclasses import dataclass


@dataclass
class PhysiologyParams:
    gb: float = 110.0
    ib: float = 15.0
    p1: float = 0.010
    p2: float = 0.020
    p3: float = 0.00012
    n: float = 0.120
    vi: float = 12.0
    body_weight_kg: float = 70.0


@dataclass
class EKFConfig:
    q_g: float = 8.0
    q_x: float = 0.02
    q_i: float = 0.20
    r_cgm: float = 25.0
    uncertainty_q_gain: float = 1.5
    uncertainty_r_gain: float = 1.0
    max_noise_scale: float = 4.0


@dataclass
class FaultConfig:
    enable: bool = True
    residual_threshold_mg_dl: float = 25.0
    nis_threshold: float = 9.0
    trigger_count: int = 3
    clear_count: int = 2
    residual_sigma_gain: float = 0.8
    residual_uncertainty_gain: float = 20.0
    nis_uncertainty_gain: float = 2.5


@dataclass
class SmithConfig:
    delay_minutes: int = 15


@dataclass
class SBIOnlineConfig:
    enable: bool = False
    update_interval_steps: int = 12
    posterior_samples: int = 128
    robust_predictor_samples: int = 16
    risk_quantile: float = 0.25


@dataclass
class ControlConfig:
    target_glucose: float = 110.0
    basal_u_per_hr: float = 1.0
    kp: float = 0.015
    ki: float = 0.0008
    kd: float = 0.010
    uncertainty_gain: float = 1.2
    min_gain_scale: float = 0.35
    integral_limit: float = 400.0


@dataclass
class SafetyConfig:
    min_u_per_hr: float = 0.0
    max_u_per_hr: float = 6.0
    hypo_guard_glucose: float = 80.0
    severe_hypo_glucose: float = 70.0


@dataclass
class TcpConfig:
    enable: bool = False
    host: str = "127.0.0.1"
    port: int = 19090
    timeout_sec: float = 0.5
    connect_timeout_sec: float = 1.0
    strict: bool = False


@dataclass
class DelayAdaptConfig:
    alpha: float = 0.25
    extra_actuation_delay_ms: float = 0.0
    min_steps: int = 0
    max_steps: int = 30


@dataclass
class LoopConfig:
    dt_minutes: int = 5
    steps: int = 180
    random_seed: int = 7
