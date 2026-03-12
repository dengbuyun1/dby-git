from src.estimation import ResidualFaultDetector


def test_fault_detector_triggers_and_clears_alarm():
    d = ResidualFaultDetector(
        residual_threshold_mg_dl=20.0,
        nis_threshold=9.0,
        trigger_count=2,
        clear_count=2,
    )

    s0 = d.update(residual=5.0, nis=1.0)
    assert not s0.is_alarm

    s1 = d.update(residual=25.0, nis=2.0)
    assert not s1.is_alarm

    s2 = d.update(residual=21.0, nis=2.0)
    assert s2.is_alarm
    assert s2.triggered

    s3 = d.update(residual=1.0, nis=1.0)
    assert s3.is_alarm

    s4 = d.update(residual=1.0, nis=1.0)
    assert not s4.is_alarm
    assert s4.cleared
