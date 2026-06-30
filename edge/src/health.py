"""Edge health state machine and metric aggregation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HealthState:
    camera_degraded: bool = False
    inference_halted: bool = False
    inference_exhausted: bool = False

    fps: Optional[float] = None
    inference_ms: Optional[float] = None
    dropped_frames: int = 0
    queue_depth: int = 0
    connection: str = "disconnected"
    idle: bool = True

    @property
    def status(self) -> str:
        """Overall node status."""
        if self.camera_degraded or self.inference_halted:
            return "degraded"
        return "healthy"

    def metrics(self) -> dict:
        """Build the metrics block."""
        state = "idle" if self.idle else "active"
        block = {
            "dropped_frames": self.dropped_frames,
            "queue_depth": self.queue_depth,
            "connection": self.connection,
            "state": state,
        }
        if not self.idle:
            block["fps"] = self.fps
            block["inference_ms"] = self.inference_ms
        return block

    def heartbeat(self, node_id: str, timestamp: str) -> dict:
        return {
            "schema_version": 1,
            "node_id": node_id,
            "timestamp": timestamp,
            "status": self.status,
            "metrics": self.metrics(),
        }
