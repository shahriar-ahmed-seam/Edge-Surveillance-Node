from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db.models import Detection, Event
from ..db.session import get_session
from ..storage.object_store import DiskObjectStore
from .auth import require_role
from .schemas import EventOut, EventPage

router = APIRouter(prefix="/api/events", tags=["events"])


def _apply_filters(stmt, node_id, label, since, until):
    if node_id:
        stmt = stmt.where(Event.node_id == node_id)
    if since:
        stmt = stmt.where(Event.timestamp >= since)
    if until:
        stmt = stmt.where(Event.timestamp <= until)
    if label:
        stmt = stmt.where(Event.detections.any(Detection.label == label))
    return stmt


@router.get("", response_model=EventPage)
def list_events(
    db: Session = Depends(get_session),
    _user=Depends(require_role("viewer")),
    node_id: Optional[str] = None,
    label: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = _apply_filters(
        select(Event).options(selectinload(Event.detections)), node_id, label, since, until
    )
    count_stmt = _apply_filters(
        select(func.count()).select_from(Event), node_id, label, since, until
    )
    total = db.execute(count_stmt).scalar_one()
    stmt = stmt.order_by(Event.timestamp.desc()).limit(limit).offset(offset)
    items = db.execute(stmt).scalars().all()
    return EventPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: str, db: Session = Depends(get_session), _user=Depends(require_role("viewer"))
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return event


@router.get("/{event_id}/snapshot")
def get_snapshot_url(
    event_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _user=Depends(require_role("viewer")),
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    if not event.snapshot_ref:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No snapshot for this event")
    store = request.app.state.object_store
    return {"url": store.signed_url(event.snapshot_ref), "ttl_hint_seconds": 300}


@router.get("/snapshot-file/{ref}")
def get_snapshot_file(ref: str, request: Request, _user=Depends(require_role("viewer"))):
    store = request.app.state.object_store
    if not isinstance(store, DiskObjectStore):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available for this backend")
    data = store.read(ref)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Snapshot not found")
    return Response(content=data, media_type="image/jpeg")
