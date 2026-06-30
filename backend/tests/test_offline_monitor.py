from datetime import datetime, timedelta, timezone

from app.db.models import Node
from app.ingestion.offline_monitor import find_offline_node_ids


def _node(node_id, last_seen, status="healthy"):
    n = Node(node_id=node_id, name=node_id, status=status,
             first_seen=last_seen, last_seen=last_seen, last_metrics={})
    return n


def test_node_within_timeout_stays_online():
    now = datetime(2026, 6, 30, 12, 0, 30, tzinfo=timezone.utc)
    n = _node("n1", now - timedelta(seconds=20))
    assert find_offline_node_ids([n], now, timeout_s=30) == []


def test_strict_inequality_at_exact_timeout_stays_online():
    # now - last_seen == timeout exactly -> NOT offline
    now = datetime(2026, 6, 30, 12, 0, 30, tzinfo=timezone.utc)
    n = _node("n1", now - timedelta(seconds=30))
    assert find_offline_node_ids([n], now, timeout_s=30) == []


def test_beyond_timeout_marked_offline():
    now = datetime(2026, 6, 30, 12, 0, 30, tzinfo=timezone.utc)
    n = _node("n1", now - timedelta(seconds=31))
    assert find_offline_node_ids([n], now, timeout_s=30) == ["n1"]


def test_already_offline_skipped():
    now = datetime(2026, 6, 30, 12, 0, 30, tzinfo=timezone.utc)
    n = _node("n1", now - timedelta(seconds=999), status="offline")
    assert find_offline_node_ids([n], now, timeout_s=30) == []
