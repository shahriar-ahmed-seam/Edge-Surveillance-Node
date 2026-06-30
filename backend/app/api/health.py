"""Health and readiness endpoints for Render health checks."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ..db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        return {"status": "not-ready", "detail": str(exc)}
