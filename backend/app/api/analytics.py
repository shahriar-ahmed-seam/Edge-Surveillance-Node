from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db.models import Detection, Event, Node
from ..db.session import get_session
from .auth import require_role
from .schemas import (
    AnalyticsSummary,
    ClassCount,
    LatencyPoint,
    NodeCount,
    TimePoint,
    Totals,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    db: Session = Depends(get_session),
    _user=Depends(require_role("viewer")),
    days: int = Query(7, ge=1, le=90),
    node_id: str | None = Query(None),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    def scoped(stmt):
        stmt = stmt.where(Event.timestamp >= since)
        if node_id:
            stmt = stmt.where(Event.node_id == node_id)
        return stmt

    total_events = db.execute(scoped(select(func.count()).select_from(Event))).scalar_one()

    total_detections = db.execute(
        scoped(
            select(func.count())
            .select_from(Detection)
            .join(Event, Detection.event_id == Event.event_id)
        )
    ).scalar_one()

    avg_conf = db.execute(
        scoped(
            select(func.avg(Detection.confidence)).join(
                Event, Detection.event_id == Event.event_id
            )
        )
    ).scalar_one()

    class_rows = db.execute(
        scoped(
            select(Detection.label, func.count().label("n")).join(
                Event, Detection.event_id == Event.event_id
            )
        )
        .group_by(Detection.label)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    by_class = [ClassCount(label=row[0], count=row[1]) for row in class_rows]

    node_rows = db.execute(
        scoped(select(Event.node_id, func.count().label("n")))
        .group_by(Event.node_id)
        .order_by(func.count().desc())
    ).all()
    name_map = {n.node_id: n.name for n in db.execute(select(Node)).scalars().all()}
    by_node = [
        NodeCount(node_id=row[0], name=name_map.get(row[0], row[0]), count=row[1])
        for row in node_rows
    ]
    active_nodes = len(node_rows)

    rows = db.execute(scoped(select(Event.timestamp, Event.metrics))).all()

    event_buckets: dict[str, int] = defaultdict(int)
    inf_buckets: dict[str, list] = defaultdict(list)
    fps_buckets: dict[str, list] = defaultdict(list)
    inf_all: list = []
    fps_all: list = []

    for ts, metrics in rows:
        day = _as_utc(ts).strftime("%Y-%m-%d")
        event_buckets[day] += 1
        if isinstance(metrics, dict):
            if metrics.get("inference_ms") is not None:
                inf_buckets[day].append(float(metrics["inference_ms"]))
                inf_all.append(float(metrics["inference_ms"]))
            if metrics.get("fps") is not None:
                fps_buckets[day].append(float(metrics["fps"]))
                fps_all.append(float(metrics["fps"]))

    time_series: List[TimePoint] = []
    latency_series: List[LatencyPoint] = []
    for i in range(days):
        day = (since + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        time_series.append(TimePoint(date=day, events=event_buckets.get(day, 0)))
        inf = inf_buckets.get(day, [])
        fps = fps_buckets.get(day, [])
        latency_series.append(
            LatencyPoint(
                date=day,
                avg_inference_ms=round(sum(inf) / len(inf), 1) if inf else 0.0,
                avg_fps=round(sum(fps) / len(fps), 1) if fps else 0.0,
            )
        )

    totals = Totals(
        events=total_events,
        detections=total_detections,
        active_nodes=active_nodes,
        avg_confidence=round(float(avg_conf), 3) if avg_conf is not None else 0.0,
        avg_inference_ms=round(sum(inf_all) / len(inf_all), 1) if inf_all else 0.0,
        avg_fps=round(sum(fps_all) / len(fps_all), 1) if fps_all else 0.0,
    )

    return AnalyticsSummary(
        range_days=days,
        generated_at=now,
        totals=totals,
        time_series=time_series,
        latency_series=latency_series,
        by_class=by_class,
        by_node=by_node,
    )


@router.get("/export")
def export(
    db: Session = Depends(get_session),
    _user=Depends(require_role("viewer")),
    fmt: str = Query("csv", pattern="^(csv|json)$"),
    days: int = Query(7, ge=1, le=90),
    node_id: str | None = Query(None),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(Event).options(selectinload(Event.detections)).where(Event.timestamp >= since)
    if node_id:
        stmt = stmt.where(Event.node_id == node_id)
    stmt = stmt.order_by(Event.timestamp.desc()).limit(50000)
    events = db.execute(stmt).scalars().all()

    records = [
        {
            "event_id": e.event_id,
            "node_id": e.node_id,
            "timestamp": e.timestamp.isoformat(),
            "label": d.label,
            "confidence": round(d.confidence, 4),
            "bbox": d.bbox,
            "snapshot_ref": e.snapshot_ref or "",
        }
        for e in events
        for d in e.detections
    ]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = f"-{node_id}" if node_id else ""

    if fmt == "json":
        return Response(
            content=json.dumps(records, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=detections{suffix}-{stamp}.json"},
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["event_id", "node_id", "timestamp", "label", "confidence", "bbox", "snapshot_ref"])
    for r in records:
        writer.writerow([
            r["event_id"], r["node_id"], r["timestamp"], r["label"],
            r["confidence"], " ".join(str(v) for v in r["bbox"]), r["snapshot_ref"],
        ])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=detections{suffix}-{stamp}.csv"},
    )
