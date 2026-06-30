"""Camera capture with a lifecycle state machine."""
from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("edge.camera")


class CameraState(enum.Enum):
    OPENING = "opening"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"


class _CV2Capture:
    """Thin wrapper to allow injecting a fake VideoCapture in tests."""

    def __init__(self, source):
        import cv2  # imported lazily so tests need not have OpenCV

        self._cv2 = cv2
        # numeric source -> device index, otherwise treat as path/URL
        try:
            src = int(source)
        except (ValueError, TypeError):
            src = source
        self._cap = cv2.VideoCapture(src)

    def is_opened(self) -> bool:
        return bool(self._cap.isOpened())

    def read(self):
        return self._cap.read()

    def release(self) -> None:
        try:
            self._cap.release()
        except Exception:  # pragma: no cover
            pass


class CameraSource:
    """Threaded camera source with health tracking and reconnection."""

    def __init__(
        self,
        source: str,
        *,
        target_fps: float = 12.0,
        failure_threshold: int = 10,
        recovery_reads: int = 15,
        backoff_base_s: float = 1.0,
        backoff_max_s: float = 30.0,
        capture_factory=_CV2Capture,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        self._source = source
        self._frame_interval = 1.0 / target_fps if target_fps > 0 else 0.0
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_reads = max(1, recovery_reads)
        self._backoff_base = backoff_base_s
        self._backoff_max = backoff_max_s
        self._capture_factory = capture_factory
        self._clock = clock
        self._sleep = sleep

        self._state = CameraState.OPENING
        self._cap = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._reconnect_attempts = 0

        self._lock = threading.Lock()
        self._latest: Optional[np.ndarray] = None
        self._latest_ts: float = 0.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- public API -------------------------------------------------------
    @property
    def state(self) -> CameraState:
        return self._state

    @property
    def is_degraded(self) -> bool:
        return self._state in (CameraState.DEGRADED, CameraState.RECONNECTING)

    def latest_frame(self):
        """Return (frame, timestamp) for the most recent successful read."""
        with self._lock:
            if self._latest is None:
                return None, 0.0
            return self._latest, self._latest_ts

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._release()

    # -- internals --------------------------------------------------------
    def _open(self) -> bool:
        self._release()
        try:
            self._cap = self._capture_factory(self._source)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Camera open raised: %s", exc)
            self._cap = None
            return False
        opened = bool(self._cap and self._cap.is_opened())
        if not opened:
            logger.warning("Camera source %r failed to open", self._source)
        return opened

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _backoff_delay(self) -> float:
        delay = self._backoff_base * (2 ** max(0, self._reconnect_attempts - 1))
        return min(delay, self._backoff_max)

    def _enter_degraded(self) -> None:
        if self._state != CameraState.DEGRADED:
            logger.error(
                "Camera entering DEGRADED after %d consecutive failures",
                self._consecutive_failures,
            )
        self._state = CameraState.DEGRADED
        self._consecutive_successes = 0

    def _on_success(self, frame) -> None:
        self._consecutive_failures = 0
        with self._lock:
            self._latest = frame
            self._latest_ts = self._clock()
        if self.is_degraded:
            self._consecutive_successes += 1
            # Recovery requires demonstrated stable capture.
            if self._consecutive_successes >= self._recovery_reads:
                logger.info(
                    "Camera recovered: %d consecutive good reads", self._consecutive_successes
                )
                self._state = CameraState.HEALTHY
                self._reconnect_attempts = 0
                self._consecutive_successes = 0
        else:
            self._state = CameraState.HEALTHY

    def _on_failure(self) -> None:
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        logger.warning(
            "Frame read failed (%d/%d)", self._consecutive_failures, self._failure_threshold
        )
        if self._consecutive_failures >= self._failure_threshold:
            self._enter_degraded()

    def _reconnect(self) -> None:
        self._state = CameraState.RECONNECTING
        self._reconnect_attempts += 1
        delay = self._backoff_delay()
        logger.info(
            "Reconnect attempt %d, backing off %.1fs", self._reconnect_attempts, delay
        )
        self._sleep(delay)
        if self._open():
            # Stay degraded until stable reads confirm recovery.
            self._state = CameraState.DEGRADED
            self._consecutive_failures = 0

    def step(self) -> None:
        """Execute a single iteration of the capture loop (testable unit)."""
        if self._cap is None or not self._cap.is_opened():
            self._reconnect()
            return

        ok, frame = self._cap.read()
        # A read can fail either by ok=False or by returning None (corrupt frame).
        if ok and frame is not None:
            self._on_success(frame)
        else:
            self._on_failure()
            # Once degraded, drive reconnection even if the device claims to be
            # open.
            if self.is_degraded:
                self._reconnect()

    def _run(self) -> None:
        if not self._open():
            self._enter_degraded()
        while not self._stop.is_set():
            start = self._clock()
            self.step()
            if self._frame_interval:
                elapsed = self._clock() - start
                remaining = self._frame_interval - elapsed
                if remaining > 0:
                    self._sleep(remaining)
