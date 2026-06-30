"""Pydantic schemas validating inbound MQTT messages."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class DetectionIn(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: List[float]

    @field_validator("bbox")
    @classmethod
    def _bbox_len(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError("bbox must have 4 elements [x, y, w, h]")
        return v


class SnapshotIn(BaseModel):
    present: bool = False
    format: Optional[str] = None
    bytes: int = 0
    omitted_reason: Optional[str] = None
    data_b64: Optional[str] = None


class EventIn(BaseModel):
    schema_version: int = 1
    node_id: str
    event_id: str
    timestamp: datetime
    detections: List[DetectionIn]
    metrics: dict = Field(default_factory=dict)
    snapshot: Optional[SnapshotIn] = None


class HeartbeatIn(BaseModel):
    schema_version: int = 1
    node_id: str
    timestamp: datetime
    status: str
    metrics: dict = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def _status_valid(cls, v: str) -> str:
        if v not in {"healthy", "degraded", "offline"}:
            raise ValueError(f"invalid status {v!r}")
        return v


__all__ = ["EventIn", "HeartbeatIn", "DetectionIn", "SnapshotIn", "ValidationError"]
