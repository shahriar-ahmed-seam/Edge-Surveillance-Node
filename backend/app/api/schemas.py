"""API response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class NodeOut(BaseModel):
    node_id: str
    name: str
    status: str
    first_seen: datetime
    last_seen: datetime
    last_metrics: dict

    class Config:
        from_attributes = True


class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: List[float]

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    event_id: str
    node_id: str
    timestamp: datetime
    snapshot_ref: Optional[str]
    snapshot_omitted_reason: Optional[str]
    metrics: dict
    detections: List[DetectionOut]

    class Config:
        from_attributes = True


class EventPage(BaseModel):
    items: List[EventOut]
    total: int
    limit: int
    offset: int


# --- Analytics ---

class Totals(BaseModel):
    events: int
    detections: int
    active_nodes: int
    avg_confidence: float
    avg_inference_ms: float
    avg_fps: float


class TimePoint(BaseModel):
    date: str
    events: int


class LatencyPoint(BaseModel):
    date: str
    avg_inference_ms: float
    avg_fps: float


class ClassCount(BaseModel):
    label: str
    count: int


class NodeCount(BaseModel):
    node_id: str
    name: str
    count: int


class AnalyticsSummary(BaseModel):
    range_days: int
    generated_at: datetime
    totals: Totals
    time_series: List[TimePoint]
    latency_series: List[LatencyPoint]
    by_class: List[ClassCount]
    by_node: List[NodeCount]
