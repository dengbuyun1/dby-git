from __future__ import annotations


class SafetySupervisor:
    def __init__(self, min_u_per_hr: float, max_u_per_hr: float, hypo_guard_glucose: float, severe_hypo_glucose: float):
        self.min_u_per_hr = float(min_u_per_hr)
        self.max_u_per_hr = float(max_u_per_hr)
        self.hypo_guard_glucose = float(hypo_guard_glucose)
        self.severe_hypo_glucose = float(severe_hypo_glucose)

    def filter_u_per_hr(self, raw_u_per_hr: float, current_glucose: float, predicted_glucose: float) -> float:
        u = float(raw_u_per_hr)

        if predicted_glucose <= self.severe_hypo_glucose:
            return 0.0

        if current_glucose <= self.hypo_guard_glucose:
            u = min(u, self.min_u_per_hr)

        return max(self.min_u_per_hr, min(self.max_u_per_hr, u))
