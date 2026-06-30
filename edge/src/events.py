"""Detection event construction with confidence gating and per-class debounce."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("edge.events")

SCHEMA_VERSION = 1


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: List[float]  # [x, y, w, h]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": round(float(self.confidence), 4),
            "bbox": [round(float(v), 2) for v in self.bbox],
        }


class EventFactory:
    def __init__(
        self,
        node_id: str,
        *,
        confidence_threshold: float = 0.45,
        debounce_seconds: float = 5.0,
        clock=time.monotonic,
    ):
        self._node_id = node_id
        self._threshold = confidence_threshold
        self._debounce = debounce_seconds
        self._clock = clock
        self._last_emit: Dict[str, float] = {}

    def _passes_debounce(self, labels: List[str], now: float) -> List[str]:
        allowed = []
        for label in labels:
            last = self._last_emit.get(label)
            if last is None or (now - last) >= self._debounce:
                allowed.append(label)
        return allowed

    def build(
        self,
        detections: List[Detection],
        *,
        metrics: Optional[dict] = None,
        snapshot_meta: Optional[dict] = None,
    ) -> Optional[dict]:
        """Build a detection event, or return None if nothing qualifies."""
        qualifying = [d for d in detections if d.confidence >= self._threshold]
        if not qualifying:
            return None

        now = self._clock()
        labels = list({d.label for d in qualifying})
        allowed_labels = self._passes_debounce(labels, now)
        if not allowed_labels:
            return None

        allowed_set = set(allowed_labels)
        emitted = [d for d in qualifying if d.label in allowed_set]
        for label in allowed_labels:
            self._last_emit[label] = now

        event = {
            "schema_version": SCHEMA_VERSION,
            "node_id": self._node_id,
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "detections": [d.to_dict() for d in emitted],
            "metrics": metrics or {},
        }
        if snapshot_meta is not None:
            event["snapshot"] = snapshot_meta
        return event
