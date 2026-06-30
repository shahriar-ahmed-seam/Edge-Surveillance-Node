import dataclasses
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.auth import create_access_token, hash_password
from app.config import load_settings
from app.db import session as session_mod
from app.db.models import Detection, Event, Node, User
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path}/api.db"
    settings = dataclasses.replace(
        load_settings(exit_on_error=False),
        database_url=url,
        storage_backend="disk",
        disk_storage_path=str(tmp_path / "snaps"),
        mqtt_use_tls=False,
    )
    app = create_app(settings)
    with TestClient(app) as c:
        # seed data after schema applied by lifespan
        with session_mod.session_scope() as db:
            db.add(User(email="admin@x.com", password_hash=hash_password("pw"), role="admin"))
            db.add(User(email="view@x.com", password_hash=hash_password("pw"), role="viewer"))
            node = Node(node_id="n1", name="n1", status="healthy",
                        first_seen=datetime.now(timezone.utc),
                        last_seen=datetime.now(timezone.utc), last_metrics={})
            db.add(node)
            for i in range(3):
                e = Event(event_id=f"e{i}", node_id="n1",
                          timestamp=datetime(2026, 6, 30, 12, i, tzinfo=timezone.utc),
                          created_at=datetime.now(timezone.utc), metrics={})
                e.detections.append(Detection(label="person" if i < 2 else "car",
                                               confidence=0.9, bbox=[0, 0, 1, 1]))
                db.add(e)
        c.app.state._settings = settings
        yield c, settings


def _auth(settings, role="admin", email="admin@x.com"):
    token = create_access_token(settings, subject=email, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_health_open(client):
    c, _ = client
    assert c.get("/healthz").json()["status"] == "ok"


def test_login_returns_token(client):
    c, _ = client
    r = c.post("/api/auth/login", json={"email": "admin@x.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_login_bad_credentials(client):
    c, _ = client
    r = c.post("/api/auth/login", json={"email": "admin@x.com", "password": "nope"})
    assert r.status_code == 401


def test_nodes_requires_auth(client):
    c, _ = client
    assert c.get("/api/nodes").status_code == 401


def test_nodes_listed_with_auth(client):
    c, settings = client
    r = c.get("/api/nodes", headers=_auth(settings))
    assert r.status_code == 200
    assert r.json()[0]["node_id"] == "n1"


def test_events_pagination(client):
    c, settings = client
    r = c.get("/api/events?limit=2", headers=_auth(settings))
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_events_filter_by_label(client):
    c, settings = client
    r = c.get("/api/events?label=car", headers=_auth(settings))
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["detections"][0]["label"] == "car"


def test_ws_rejects_without_token(client):
    c, _ = client
    with pytest.raises(Exception):
        with c.websocket_connect("/ws/events"):
            pass


def test_ws_accepts_with_token(client):
    c, settings = client
    token = create_access_token(settings, subject="admin@x.com", role="admin")
    with c.websocket_connect(f"/ws/events?token={token}") as wsconn:
        # connection accepted; no message expected yet (no real event)
        assert wsconn is not None
