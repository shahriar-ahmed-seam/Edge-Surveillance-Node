import base64
import json

from app.db.models import Event, Node
from app.ingestion.worker import IngestionWorker


class FakeStore:
    def __init__(self):
        self.saved = []

    def put_snapshot(self, data, content_type="image/jpeg"):
        self.saved.append(data)
        return f"ref-{len(self.saved)}"

    def signed_url(self, ref):
        return f"http://x/{ref}"


class FakeBus:
    def __init__(self):
        self.published = []
        self.committed_at_publish = []

    def publish_threadsafe(self, message):
        self.published.append(message)


def _settings_stub():
    class S:
        mqtt_topic_events = "nodes/+/events"
        mqtt_topic_heartbeat = "nodes/+/heartbeat"
    return S()


def _event_payload(event_id="e1", with_snapshot=False):
    payload = {
        "schema_version": 1,
        "node_id": "n1",
        "event_id": event_id,
        "timestamp": "2026-06-30T12:00:00Z",
        "detections": [{"label": "person", "confidence": 0.9, "bbox": [1, 2, 3, 4]}],
        "metrics": {"fps": 11.0},
    }
    if with_snapshot:
        payload["snapshot"] = {
            "present": True, "format": "jpeg", "bytes": 3,
            "omitted_reason": None, "data_b64": base64.b64encode(b"abc").decode(),
        }
    return json.dumps(payload).encode()


def test_event_persisted_and_published_after_commit(db_session):
    bus = FakeBus()
    store = FakeStore()
    worker = IngestionWorker(_settings_stub(), store, bus)

    worker.handle_message("nodes/n1/events", _event_payload())

    # persisted
    with db_session.session_scope() as db:
        event = db.get(Event, "e1")
        assert event is not None
        assert event.node_id == "n1"
        assert len(event.detections) == 1
    # published after commit
    assert len(bus.published) == 1
    assert bus.published[0]["event_id"] == "e1"


def test_snapshot_stored_by_reference(db_session):
    bus = FakeBus()
    store = FakeStore()
    worker = IngestionWorker(_settings_stub(), store, bus)
    worker.handle_message("nodes/n1/events", _event_payload(with_snapshot=True))

    assert store.saved == [b"abc"]
    with db_session.session_scope() as db:
        event = db.get(Event, "e1")
        assert event.snapshot_ref == "ref-1"


def test_malformed_event_rejected_no_publish(db_session):
    bus = FakeBus()
    worker = IngestionWorker(_settings_stub(), FakeStore(), bus)
    worker.handle_message("nodes/n1/events", b'{"node_id": "n1"}')  # missing fields
    assert bus.published == []  # no event => no push


def test_heartbeat_updates_node_state(db_session):
    bus = FakeBus()
    worker = IngestionWorker(_settings_stub(), FakeStore(), bus)
    hb = json.dumps({
        "schema_version": 1, "node_id": "n1", "timestamp": "2026-06-30T12:00:00Z",
        "status": "degraded", "metrics": {"fps": 5},
    }).encode()
    worker.handle_message("nodes/n1/heartbeat", hb)
    with db_session.session_scope() as db:
        node = db.get(Node, "n1")
        assert node is not None
        assert node.status == "degraded"


def test_duplicate_event_ignored(db_session):
    bus = FakeBus()
    worker = IngestionWorker(_settings_stub(), FakeStore(), bus)
    worker.handle_message("nodes/n1/events", _event_payload("dup"))
    worker.handle_message("nodes/n1/events", _event_payload("dup"))
    with db_session.session_scope() as db:
        count = len(list(db.execute(__import__("sqlalchemy").select(Event)).scalars()))
    assert count == 1
