"""Authenticated WebSocket hub for live event push."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..config import Settings
from .auth import AuthError, decode_token

logger = logging.getLogger("backend.ws")

router = APIRouter()


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    settings: Settings = websocket.app.state.settings
    bus = websocket.app.state.event_bus

    # Token may arrive as a query param (?token=) or Authorization header.
    token = websocket.query_params.get("token")
    if not token:
        auth = websocket.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_token(settings, token)
    except AuthError:
        # Reject before any data is delivered.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    queue = bus.subscribe()
    logger.info("WebSocket client connected")
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover - network
        logger.debug("WS send loop ended: %s", exc)
    finally:
        bus.unsubscribe(queue)
        logger.info("WebSocket client disconnected")
