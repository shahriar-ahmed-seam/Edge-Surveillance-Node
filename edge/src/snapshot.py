"""JPEG snapshot encoding with compress-to-fit behavior."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger("edge.snapshot")

_QUALITY_STEPS = (90, 75, 60, 45)


@dataclass
class SnapshotResult:
    data: Optional[bytes]
    quality: Optional[int]
    omitted_reason: Optional[str]

    @property
    def present(self) -> bool:
        return self.data is not None


class SnapshotEncoder:
    def __init__(
        self,
        *,
        max_bytes: int = 51200,
        min_quality: int = 30,
        encode_fn=None,
        resize_fn=None,
    ):
        self._max_bytes = max_bytes
        self._min_quality = min_quality
        self._encode_fn = encode_fn or self._cv2_encode
        self._resize_fn = resize_fn or self._cv2_resize

    @staticmethod
    def _cv2_encode(frame: np.ndarray, quality: int) -> bytes:
        import cv2

        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return buf.tobytes()

    @staticmethod
    def _cv2_resize(frame: np.ndarray, scale: float) -> np.ndarray:
        import cv2

        h, w = frame.shape[:2]
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    def encode(self, frame: np.ndarray) -> SnapshotResult:
        """Encode a frame to a size-bounded JPEG.

        Strategy: step quality down; if still too large, downscale and retry at
        the minimum quality. Only if the minimum-quality, downscaled image still
        exceeds the limit do we omit, with a reason flag.
        """
        # 1. Try decreasing quality at full resolution.
        quality_levels = [q for q in _QUALITY_STEPS if q >= self._min_quality]
        quality_levels.append(self._min_quality)
        for quality in quality_levels:
            data = self._encode_fn(frame, quality)
            if len(data) <= self._max_bytes:
                return SnapshotResult(data=data, quality=quality, omitted_reason=None)

        # 2. Downscale progressively at minimum quality.
        for scale in (0.75, 0.5, 0.35, 0.25):
            scaled = self._resize_fn(frame, scale)
            data = self._encode_fn(scaled, self._min_quality)
            if len(data) <= self._max_bytes:
                logger.info("Snapshot fit after downscale to %.0f%%", scale * 100)
                return SnapshotResult(
                    data=data, quality=self._min_quality, omitted_reason=None
                )

        # 3. Last resort: omit with an explicit flag.
        logger.warning(
            "Snapshot omitted: cannot fit under %d bytes at min quality", self._max_bytes
        )
        return SnapshotResult(
            data=None, quality=None, omitted_reason="exceeds_max_size"
        )
