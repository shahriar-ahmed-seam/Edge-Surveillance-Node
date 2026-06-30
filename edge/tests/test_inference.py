import numpy as np
import pytest

from src.inference import Detector, InferenceError, _nms


def test_nms_removes_overlapping_boxes():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 10, 10], [100, 100, 10, 10]], dtype=float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = _nms(boxes, scores, 0.5)
    assert 0 in keep
    assert 2 in keep
    assert 1 not in keep  # suppressed by overlap with 0


def test_load_failure_raises_and_halts():
    def bad_factory(path):
        raise RuntimeError("cannot open")

    det = Detector("missing.onnx", session_factory=bad_factory)
    with pytest.raises(InferenceError):
        det.load()
    assert det.halted


class FakeSession:
    def __init__(self, output=None, raise_on_run=False):
        self._output = output
        self._raise = raise_on_run

    def get_inputs(self):
        class I:
            name = "input"

        return [I()]

    def run(self, _outputs, _feed):
        if self._raise:
            raise RuntimeError("kernel crash")
        return [self._output]


def test_runtime_inference_failure_halts(monkeypatch):
    det = Detector("m.onnx", session_factory=lambda p: FakeSession(raise_on_run=True))
    det.load()
    assert not det.halted
    # bypass preprocessing (needs cv2) by monkeypatching
    det._preprocess = lambda frame: np.zeros((1, 3, 8, 8), dtype=np.float32)
    with pytest.raises(InferenceError):
        det.infer(np.zeros((8, 8, 3), dtype=np.uint8))
    assert det.halted  # any inference failure halts


def test_bounded_recovery_exhaustion():
    attempts = {"n": 0}

    def factory(path):
        attempts["n"] += 1
        raise RuntimeError("still broken")

    det = Detector("m.onnx", max_recovery_attempts=3, session_factory=factory)
    det._halted = True
    results = [det.attempt_recovery() for _ in range(5)]
    assert results[:3] == [False, False, False]
    # after exhaustion, no further attempts are made
    assert det.exhausted
    assert attempts["n"] == 3


def test_successful_inference_records_metrics():
    output = np.array([[1, 1, 5, 5, 0.9, 0]], dtype=float)
    det = Detector("m.onnx", confidence_threshold=0.5,
                   session_factory=lambda p: FakeSession(output=output),
                   labels=["person"], clock=_seq_clock())
    det.load()
    det._preprocess = lambda frame: np.zeros((1, 3, 8, 8), dtype=np.float32)
    det._postprocess = Detector._postprocess.__get__(det)
    # monkeypatch cv2-dependent postprocess scaling by faking frame shape
    dets = det.infer(np.zeros((10, 10, 3), dtype=np.uint8))
    assert det.metrics.idle is False
    assert det.metrics.inference_ms >= 0
    assert len(dets) == 1
    assert dets[0].label == "person"


def _seq_clock():
    state = {"t": 0.0}

    def clock():
        state["t"] += 0.01
        return state["t"]

    return clock
