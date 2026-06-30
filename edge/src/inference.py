"""Quantized ONNX inference engine."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from .events import Detection

logger = logging.getLogger("edge.inference")


class InferenceError(Exception):
    """Raised when the model cannot load or inference cannot proceed."""


def load_labels(path: str) -> List[str]:
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip()]
    except OSError as exc:
        logger.warning("Could not load labels from %s: %s", path, exc)
        return []


@dataclass
class InferenceMetrics:
    inference_ms: float = 0.0
    fps: float = 0.0
    idle: bool = True


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
    """Pure-numpy non-max suppression. boxes are [x, y, w, h]."""
    if len(boxes) == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= iou_threshold]
    return keep


class Detector:
    """ONNX Runtime detector with metrics and bounded failure recovery."""

    def __init__(
        self,
        model_path: str,
        *,
        labels: Optional[List[str]] = None,
        input_size: int = 320,
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        max_recovery_attempts: int = 5,
        session_factory=None,
        clock=time.monotonic,
    ):
        self._model_path = model_path
        self._labels = labels or []
        self._input_size = input_size
        self._conf = confidence_threshold
        self._iou = iou_threshold
        self._max_recovery = max_recovery_attempts
        self._session_factory = session_factory or self._ort_session
        self._clock = clock

        self._session = None
        self._input_name: Optional[str] = None
        self._halted = False
        self._recovery_attempts = 0
        self._metrics = InferenceMetrics()

    @property
    def halted(self) -> bool:
        return self._halted

    @property
    def metrics(self) -> InferenceMetrics:
        return self._metrics

    @property
    def exhausted(self) -> bool:
        """True when bounded recovery is used up; requires manual intervention."""
        return self._halted and self._recovery_attempts >= self._max_recovery

    def _ort_session(self, model_path: str):
        import onnxruntime as ort

        return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    def load(self) -> None:
        """Load the model. Raises InferenceError on failure."""
        try:
            self._session = self._session_factory(self._model_path)
            self._input_name = self._session.get_inputs()[0].name
            self._halted = False
            logger.info("Loaded model %s", self._model_path)
        except Exception as exc:
            self._halted = True
            raise InferenceError(f"Failed to load model {self._model_path}: {exc}") from exc

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        import cv2

        resized = cv2.resize(frame, (self._input_size, self._input_size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        chw = rgb.astype(np.float32).transpose(2, 0, 1) / 255.0
        return chw[np.newaxis, ...]

    def _postprocess(self, outputs, frame_shape) -> List[Detection]:
        """Decode model outputs into detections.

        Expects an output of shape [N, 6] = [x, y, w, h, score, class_id]
        in input-resolution pixel coords. Adapt for your specific model head.
        """
        raw = np.asarray(outputs[0])
        raw = raw.reshape(-1, raw.shape[-1])
        if raw.shape[1] < 6:
            raise InferenceError(f"Unexpected output shape {raw.shape}")

        boxes = raw[:, :4]
        scores = raw[:, 4]
        class_ids = raw[:, 5].astype(int)

        mask = scores >= self._conf
        boxes, scores, class_ids = boxes[mask], scores[mask], class_ids[mask]
        if len(boxes) == 0:
            return []

        keep = _nms(boxes, scores, self._iou)
        h, w = frame_shape[:2]
        sx, sy = w / self._input_size, h / self._input_size
        detections: List[Detection] = []
        for i in keep:
            x, y, bw, bh = boxes[i]
            cid = class_ids[i]
            label = self._labels[cid] if 0 <= cid < len(self._labels) else f"class_{cid}"
            detections.append(
                Detection(
                    label=label,
                    confidence=float(scores[i]),
                    bbox=[float(x * sx), float(y * sy), float(bw * sx), float(bh * sy)],
                )
            )
        return detections

    def infer(self, frame: np.ndarray) -> List[Detection]:
        """Run inference on a frame."""
        if self._session is None:
            self._halted = True
            raise InferenceError("Model not loaded")
        try:
            start = self._clock()
            tensor = self._preprocess(frame)
            outputs = self._session.run(None, {self._input_name: tensor})
            detections = self._postprocess(outputs, frame.shape)
            elapsed_ms = (self._clock() - start) * 1000.0
            fps = 1000.0 / elapsed_ms if elapsed_ms > 0 else 0.0
            self._metrics = InferenceMetrics(
                inference_ms=round(elapsed_ms, 2), fps=round(fps, 2), idle=False
            )
            self._recovery_attempts = 0  # successful inference resets recovery
            return detections
        except InferenceError:
            self._halted = True
            raise
        except Exception as exc:
            self._halted = True
            raise InferenceError(f"Inference failed: {exc}") from exc

    def attempt_recovery(self) -> bool:
        """Try to reload the model within the bounded attempt budget."""
        if self._recovery_attempts >= self._max_recovery:
            logger.error(
                "Inference recovery exhausted after %d attempts; manual intervention required",
                self._recovery_attempts,
            )
            return False
        self._recovery_attempts += 1
        logger.info("Inference recovery attempt %d/%d", self._recovery_attempts, self._max_recovery)
        try:
            self.load()
            return True
        except InferenceError as exc:
            logger.warning("Recovery attempt failed: %s", exc)
            self._halted = True
            return False
