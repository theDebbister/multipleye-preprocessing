import preprocessing.signals.preprocess as preprocess_module
from preprocessing import settings


class _FakeExperiment:
    sampling_rate = 1000


class _FakeGaze:
    def __init__(self):
        self.experiment = _FakeExperiment()
        self.pix2deg_called = False
        self.pos2vel_calls = []

    def pix2deg(self):
        self.pix2deg_called = True

    def pos2vel(self, method, window_length=None, degree=None):
        self.pos2vel_calls.append((method, window_length, degree))


def test_preprocess_gaze_uses_settings(monkeypatch):
    monkeypatch.setattr(settings, "VELOCITY_ESTIMATION_METHOD", "fivepoint")
    monkeypatch.setattr(settings, "VELOCITY_SMOOTHING_WINDOW_MS", 100)
    monkeypatch.setattr(settings, "VELOCITY_POLYNOMIAL_DEGREE", 3)

    gaze = _FakeGaze()
    preprocess_module.preprocess_gaze(gaze)

    assert gaze.pix2deg_called
    # window_length = round(1000 / 1000 * 100) = 100 -> even -> +1 = 101
    assert gaze.pos2vel_calls == [("fivepoint", 101, 3)]


def test_preprocess_gaze_explicit_args_override_settings(monkeypatch):
    monkeypatch.setattr(settings, "VELOCITY_ESTIMATION_METHOD", "fivepoint")
    monkeypatch.setattr(settings, "VELOCITY_SMOOTHING_WINDOW_MS", 100)
    monkeypatch.setattr(settings, "VELOCITY_POLYNOMIAL_DEGREE", 3)

    gaze = _FakeGaze()
    preprocess_module.preprocess_gaze(
        gaze, method="savitzky_golay", window_ms=20, poly_degree=2
    )

    # window_length = round(1000 / 1000 * 20) = 20 -> even -> +1 = 21
    assert gaze.pos2vel_calls == [("savitzky_golay", 21, 2)]
