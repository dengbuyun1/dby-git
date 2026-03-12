from .base import Controller, Action


class MyController(Controller):
    def __init__(self):
        self.init_state = None
        self.prev_glucose = None

    def policy(self, observation, reward, done, **info):
        # Get current glucose (CGM)
        glucose = observation.CGM if hasattr(observation, "CGM") else 120

        # Basic insulin rate (U/min)
        basal = 0.05  # About 3 U/h
        bolus = 0.0

        # Adjust based on glucose level
        if glucose > 180:  # High glucose
            bolus = min(0.1, (glucose - 180) / 100)
        elif glucose > 150:
            bolus = min(0.05, (glucose - 150) / 100)
        elif glucose < 80:  # Low glucose
            basal = max(0.01, basal * 0.5)

        # Consider glucose trend
        if self.prev_glucose is not None:
            glucose_rate = glucose - self.prev_glucose
            if glucose_rate > 5:  # Rising fast
                bolus += 0.02
            elif glucose_rate < -5:  # Falling fast
                basal = max(0.01, basal * 0.8)

        self.prev_glucose = glucose

        return Action(basal=basal, bolus=bolus)

    def reset(self):
        self.prev_glucose = None
