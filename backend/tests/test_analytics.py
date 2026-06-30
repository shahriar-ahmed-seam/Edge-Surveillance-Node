import dataclasses
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.auth import create_access_token, hash_password
from app.config import load_settings
from app.db import session as session_mod
from app.db.models import Detection, Event, Node, User
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path}/analytics.db"
    settings = dataclasses.replace(
        load_settings(exit_on_error=False),
        database_url=url,
        storage_backend="disk",
        disk_storage_path=str(tmp_path / "snaps"),
        mqtt_use_tls=False,
    )
    app = create_app(settings)
    now = datetime.now(timezone.utc)
    with TestClient(app) as c:
        with session_mod.session_scope() as db:
            db.add(User(email="a@x.com", password_hash=hash_password("pw"), role="admin"))
            db.add(Node(node_id="n1", name="Cam One", status="healthy",
                        first_seen=now, last_seen=now, last_metrics={}))
            db.add(Node(node_id="n2", name="Cam Two", status="healthy",
                        first_seen=now, last_seen=now, last_metrics={}))
            # events spread over 3 days, varied classes/metrics
            specs = [
                ("n1", 0, "person", 0.9, 40.0, 12.0),
                ("n1", 0, "car", 0.8, 42.0, 11.0),
                ("n1", 1, "person", 0.7, 38.0, 13.0),
                ("n2", 1, "dog", 0.6, 50.0, 10.0),
                ("n2", 2, "person", 0.95, 36.0, 14.0),
            ]
            for i, (node, days_ago, label, conf, inf, fps) in enumerate(specs):
                e = Event(
                    event_id=f"e{i}", node_id=node,
                    timestamp=now - timedelta(days=days_ago, hours=1),
                    created_at=now, metrics={"inference_ms": inf, "fps": fps},
                )
                e.detections.append(Detection(label=label, confidence=conf, bbox=[0, 0, 1, 1]))
                db.add(e)
        yield c, settings


def _auth(settings):
    return {"Authorization": f"Bearer {create_access_token(settings, subject='a@x.com', role='admin')}"}


def test_summary_requires_auth(client):
    c, _ = client
    assert c.get("/api/analytics/summary").status_code == 401


def test_summary_totals(client):
    c, settings = client
    r = c.get("/api/analytics/summary?days=7", headers=_auth(settings))
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["events"] == 5
    assert body["totals"]["detections"] == 5
    assert body["totals"]["active_nodes"] == 2
    assert 0 < body["totals"]["avg_confidence"] <= 1
    assert body["totals"]["avg_inference_ms"] > 0


def test_summary_class_distribution(client):
    c, settings = client
    body = c.get("/api/analytics/summary", headers=_auth(settings)).json()
    classes = {c_["label"]: c_["count"] for c_ in body["by_class"]}
    assert classes["person"] == 3  # most frequent class
    assert body["by_class"][0]["label"] == "person"


def test_summary_time_series_is_continuous(client):
    c, settings = client
    body = c.get("/api/analytics/summary?days=7", headers=_auth(settings)).json()
    # one bucket per day in the range
    assert len(body["time_series"]) == 7
    assert sum(p["events"] for p in body["time_series"]) == 5
    assert len(body["latency_series"]) == 7


def test_summary_by_node(client):
    c, settings = client
    body = c.get("/api/analytics/summary", headers=_auth(settings)).json()
    by_node = {n["node_id"]: n["count"] for n in body["by_node"]}
    assert by_node["n1"] == 3
    assert by_node["n2"] == 2
    assert any(n["name"] == "Cam One" for n in body["by_node"])


def test_summary_node_filter(client):
    c, settings = client
    body = c.get("/api/analytics/summary?node_id=n1", headers=_auth(settings)).json()
    assert body["totals"]["events"] == 3
    assert all(n["node_id"] == "n1" for n in body["by_node"])


def test_export_csv(client):
    c, settings = client
    r = c.get("/api/analytics/export?fmt=csv", headers=_auth(settings))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("event_id,node_id,timestamp,label")
    assert len(lines) == 6  # header + 5 detections


def test_export_json_node_filter(client):
    c, settings = client
    r = c.get("/api/analytics/export?fmt=json&node_id=n2", headers=_auth(settings))
    assert r.status_code == 200
    data = r.json()
    assert all(item["node_id"] == "n2" for item in data)
    assert len(data) == 2


def test_export_requires_auth(client):
    c, _ = client
    assert c.get("/api/analytics/export").status_code == 401
