from src.config import PhysiologyParams
from src.model import PhysiologyModel


def test_model_applies_sbi_scales_with_clipping():
    params = PhysiologyParams(p1=0.01, p2=0.02, p3=0.00012)
    model = PhysiologyModel(params=params, dt_minutes=5)

    scales = model.apply_sbi_scales({"kp1": 1.5, "kp2": 0.7, "kp3": 1.2, "kabs": 1.8})

    assert abs(model.params.p1 - 0.015) < 1e-12
    assert abs(model.params.p2 - 0.014) < 1e-12
    assert abs(model.params.p3 - 0.000144) < 1e-12
    assert abs(model.meal_gain - 1.8) < 1e-12
    assert scales["kp1"] == 1.5


def test_model_adaptation_clip_boundaries():
    params = PhysiologyParams(p1=0.01, p2=0.02, p3=0.00012)
    model = PhysiologyModel(params=params, dt_minutes=5)

    model.apply_sbi_scales({"kp1": 10.0, "kp2": 0.01, "kp3": 3.0, "kabs": 0.0})

    assert abs(model.params.p1 - 0.02) < 1e-12
    assert abs(model.params.p2 - 0.01) < 1e-12
    assert abs(model.params.p3 - 0.00024) < 1e-12
    assert abs(model.meal_gain - 0.5) < 1e-12
