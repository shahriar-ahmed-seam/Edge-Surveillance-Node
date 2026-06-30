import pytest

from app.ingestion.validators import EventIn, HeartbeatIn, ValidationError


def test_valid_event_parses():
    payload = {
        "schema_version": 1,
        "node_id": "n1",
        "event_id": "e1",
        "timestamp": "2026-06-30T12:00:00Z",
        "detections": [{"label": "person", "confidence": 0.9, "bbox": [0, 0, 1, 1]}],
        "metrics": {"fps": 10},
    }
    evt = EventIn.model_validate(payload)
    assert evt.node_id == "n1"
    assert evt.detections[0].label == "person"


def test_event_rejects_bad_bbox():
    with pytest.raises(ValidationError):
        EventIn.model_validate({
            "node_id": "n1", "event_id": "e1", "timestamp": "2026-06-30T12:00:00Z",
            "detections": [{"label": "p", "confidence": 0.9, "bbox": [0, 0]}],
        })


def test_event_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        EventIn.model_validate({
            "node_id": "n1", "event_id": "e1", "timestamp": "2026-06-30T12:00:00Z",
            "detections": [{"label": "p", "confidence": 1.5, "bbox": [0, 0, 1, 1]}],
        })


def test_heartbeat_rejects_invalid_status():
    with pytest.raises(ValidationError):
        HeartbeatIn.model_validate({
            "node_id": "n1", "timestamp": "2026-06-30T12:00:00Z", "status": "exploded",
        })


def test_heartbeat_accepts_degraded():
    hb = HeartbeatIn.model_validate({
        "node_id": "n1", "timestamp": "2026-06-30T12:00:00Z", "status": "degraded",
    })
    assert hb.status == "degraded"
