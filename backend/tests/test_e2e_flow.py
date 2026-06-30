"""End-to-end flow test for published detections reaching WebSocket and REST clients."""
from __future__ import annotations

import dataclasses
import json
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.auth import create_access_token, hash_password
from app.config import load_settings
from app.db import session as session_mod
from app.db.models import User
from app.main import create_app


@pytest.fixture
def app_client(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path}/e2e.db"
    settings = dataclasses.replace(
        load_settings(exit_on_error=False),
        database_url=url,
        storage_backend="disk",
        disk_storage_path=str(tmp_path / "snaps"),
        mqtt_use_tls=False,
    )
    app = create_app(settings)
    with TestClient(app) as c:
        with session_mod.session_scope() as db:
            db.add(User(email="admin@x.com", password_hash=hash_password("pw"), role="admin"))
        yield c, settings


def _detection_payload(event_id="evt-e2e"):
    return json.dumps(
        {
            "schema_version": 1,
            "node_id": "node-e2e",
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detections": [{"label": "person", "confidence": 0.94, "bbox": [10, 20, 30, 40]}],
            "metrics": {"fps": 12.0, "inference_ms": 38.0},
        }
    ).encode()


def test_published_detection_reaches_ws_and_rest_within_2s(app_client):
    client, settings = app_client
    token = create_access_token(settings, subject="admin@x.com", role="admin")
    worker = client.app.state.worker

    with client.websocket_connect(f"/ws/events?token={token}") as ws:
        start = time.monotonic()
        # Simulate the agent's MQTT publish arriving at the ingestion worker.
        worker.handle_message("nodes/node-e2e/events", _detection_payload())

        # (a) pushed over WebSocket within 2 seconds
        message = ws.receive_json()
        elapsed = time.monotonic() - start
        assert elapsed < 2.0
        assert message["type"] == "detection"
        assert message["event_id"] == "evt-e2e"
        assert message["node_id"] == "node-e2e"

    # (b) retrievable via REST
    resp = client.get(
        "/api/events?node_id=node-e2e", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["event_id"] == "evt-e2e"
    assert body["items"][0]["detections"][0]["label"] == "person"


def test_no_push_without_event(app_client):
    """No synthetic pushes: a malformed message persists nothing and pushes nothing."""
    client, settings = app_client
    token = create_access_token(settings, subject="admin@x.com", role="admin")
    worker = client.app.state.worker

    with client.websocket_connect(f"/ws/events?token={token}") as ws:
        worker.handle_message("nodes/node-e2e/events", b'{"bad": "payload"}')
        # Deliver a valid one afterwards; the first valid message we receive must
        # be the good event, proving the malformed one produced no push.
        worker.handle_message("nodes/node-e2e/events", _detection_payload("good-1"))
        message = ws.receive_json()
        assert message["event_id"] == "good-1"
