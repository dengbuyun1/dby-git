import numpy as np

from src.compensation import SmithPredictor
from src.config import PhysiologyParams
from src.estimation import ExtendedKalmanFilter
from src.model import PhysiologyModel


def test_ekf_update_reduces_glucose_variance_and_has_diagnostics():
    model = PhysiologyModel(PhysiologyParams(), dt_minutes=5)
    ekf = ExtendedKalmanFilter(
        model=model,
        x0=np.array([170.0, 0.0, 15.0]),
        p0=np.diag([120.0, 0.1, 10.0]),
        q=np.diag([2.0, 0.01, 0.1]),
        r=np.array([[25.0]]),
    )

    prior_var = ekf.p[0, 0]
    ekf.predict(insulin_u_per_min=0.02, meal_effect=0.0)
    ekf.update(cgm_mg_dl=150.0)
    post_var = ekf.p[0, 0]

    diag = ekf.diagnostics
    assert post_var < prior_var
    assert diag.innovation_abs >= 0.0
    assert diag.innovation_var > 0.0
    assert diag.nis >= 0.0


def test_smith_predicts_forward_and_compensates_signal():
    model = PhysiologyModel(PhysiologyParams(), dt_minutes=5)
    smith = SmithPredictor(model=model, delay_steps=3)

    x = np.array([150.0, 0.0, 15.0])
    u_hist = [0.01, 0.01, 0.01]
    meal_hist = [0.8, 0.8, 0.8]

    x_pred = smith.predict_for_control(x, u_hist, meal_hist)
    comp = smith.compensate_signal(x, u_hist, meal_hist, measured_glucose=145.0)

    assert x_pred.shape == (3,)
    assert x_pred[0] > x[0]
    assert comp.predicted_glucose > 0.0
    assert 40.0 <= comp.corrected_glucose <= 400.0
