from __future__ import annotations


class PIDInsulinController:
    def __init__(self, target_glucose: float, basal_u_per_hr: float, kp: float, ki: float, kd: float, dt_minutes: int):
        self.target = float(target_glucose)
        self.basal_u_per_hr = float(basal_u_per_hr)
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.dt_h = float(dt_minutes) / 60.0
        self.integral = 0.0
        self.prev_error = 0.0

    def compute_u_per_hr(self, predicted_glucose: float) -> float:
        error = float(predicted_glucose) - self.target
        self.integral += error * self.dt_h
        derivative = (error - self.prev_error) / max(self.dt_h, 1e-9)
        self.prev_error = error

        u = self.basal_u_per_hr + self.kp * error + self.ki * self.integral + self.kd * derivative
        return float(u)
