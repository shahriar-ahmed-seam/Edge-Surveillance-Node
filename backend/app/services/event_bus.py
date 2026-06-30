"""In-process async pub/sub bridging ingestion to WebSocket clients."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Set

logger = logging.getLogger("backend.event_bus")


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, message: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("WS subscriber queue full; dropping message")

    def publish_threadsafe(self, message: Dict[str, Any]) -> None:
        """Publish from a non-async thread (the MQTT ingestion worker)."""
        if self._loop is None:
            logger.debug("Event bus loop not bound; dropping message")
            return
        asyncio.run_coroutine_threadsafe(self.publish(message), self._loop)
