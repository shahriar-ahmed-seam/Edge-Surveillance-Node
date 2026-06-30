import numpy as np

from src.camera import CameraSource, CameraState


class FakeCapture:
    """Scriptable VideoCapture sharing one script list across reconnections.

    Reconnection in the real world opens a fresh device that continues from the
    current state of the world; the shared list models that continuity.
    """

    def __init__(self, source, shared_script):
        self.source = source
        self._script = shared_script  # shared reference, intentionally not copied
        self._opened = True

    def is_opened(self):
        return self._opened

    def read(self):
        if self._script:
            return self._script.pop(0)
        return False, None

    def release(self):
        self._opened = False


def _frame():
    return np.zeros((4, 4, 3), dtype=np.uint8)


def _make(script, **kw):
    shared = list(script)

    def factory(source):
        return FakeCapture(source, shared)

    return CameraSource(
        "0",
        target_fps=0,  # no sleeping in tests
        failure_threshold=kw.get("failure_threshold", 3),
        recovery_reads=kw.get("recovery_reads", 2),
        capture_factory=factory,
        sleep=lambda *_: None,
        clock=lambda: 1.0,
    )


def test_successful_read_sets_healthy_and_buffers_frame():
    cam = _make([(True, _frame())])
    assert cam._open()
    cam.step()
    assert cam.state == CameraState.HEALTHY
    frame, ts = cam.latest_frame()
    assert frame is not None


def test_single_failure_does_not_degrade():
    cam = _make([(True, _frame()), (False, None)], failure_threshold=3)
    cam._open()
    cam.step()  # ok
    cam.step()  # one failure
    assert cam.state == CameraState.HEALTHY  # below threshold


def test_sustained_failures_enter_degraded():
    cam = _make([(False, None)] * 5, failure_threshold=3)
    cam._open()
    for _ in range(3):
        cam.step()
    assert cam.is_degraded


def test_corrupt_frame_counts_as_failure():
    # ok=True but frame is None -> treated as failure
    cam = _make([(True, None)] * 4, failure_threshold=3)
    cam._open()
    for _ in range(3):
        cam.step()
    assert cam.is_degraded


def test_recovery_requires_consecutive_good_reads():
    # 3 failures -> degraded, then good reads must reach recovery_reads to clear.
    script = [(False, None)] * 3 + [(True, _frame()), (True, _frame())]
    cam = _make(script, failure_threshold=3, recovery_reads=2)
    cam._open()
    for _ in range(3):
        cam.step()
    assert cam.is_degraded
    cam.step()  # 1 good read -> still degraded
    assert cam.is_degraded
    cam.step()  # 2nd good read -> recovered
    assert cam.state == CameraState.HEALTHY
