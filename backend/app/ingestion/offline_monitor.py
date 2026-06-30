"""Offline detection for fleet nodes."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select

from ..db.models import Node
from ..db.session import session_scope

logger = logging.getLogger("backend.offline_monitor")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def find_offline_node_ids(nodes: List[Node], now: datetime, timeout_s: float) -> List[str]:
    """Pure function: which currently-online nodes should be marked offline."""
    cutoff = timedelta(seconds=timeout_s)
    offline = []
    for node in nodes:
        if node.status == "offline":
            continue
        # Strict inequality: equal-to-timeout stays online.
        if (now - _as_utc(node.last_seen)) > cutoff:
            offline.append(node.node_id)
    return offline


class OfflineMonitor:
    def __init__(self, settings, clock=lambda: datetime.now(timezone.utc)):
        self._timeout = settings.node_offline_timeout_s
        self._interval = settings.offline_check_interval_s
        self._clock = clock
        self._stop = threading.Event()
        self._thread = None

    def sweep_once(self) -> List[str]:
        now = self._clock()
        with session_scope() as db:
            nodes = list(db.execute(select(Node)).scalars())
            offline_ids = find_offline_node_ids(nodes, now, self._timeout)
            for node in nodes:
                if node.node_id in offline_ids:
                    node.status = "offline"
        if offline_ids:
            logger.info("Marked %d node(s) offline: %s", len(offline_ids), offline_ids)
        return offline_ids

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.sweep_once()
            except Exception as exc:  # pragma: no cover
                logger.exception("Offline sweep failed: %s", exc)
            self._stop.wait(self._interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="offline-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
