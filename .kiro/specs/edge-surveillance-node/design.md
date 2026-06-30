# Design Document — Edge-Surveillance-Node

## Overview

Edge-Surveillance-Node is a distributed, three-tier system:

1. **Edge Agent** (Python) — runs on Raspberry Pi / Jetson Nano. Captures frames (OpenCV), runs INT8 ONNX inference, generates detection events, and publishes them over MQTT with local buffering for resilience.
2. **Cloud Backend** (Python / FastAPI, deployed to **Render**) — an MQTT subscriber + ingestion pipeline, a REST + WebSocket API, persistence (PostgreSQL), and object storage (S3-compatible) for snapshots.
3. **Operator Dashboard** (Next.js / React, deployed to **Vercel**) — a modern, professional monitoring UI with live updates.

A separate **quantization toolchain** (offline, run by ML engineers) produces the INT8 ONNX artifact consumed by the edge agent.

```
                         ┌──────────────────────────────────────────┐
   Edge Hardware         │                 Render (Cloud)             │      Vercel
 ┌───────────────┐  MQTT │  ┌─────────────┐   ┌──────────────────┐    │   ┌──────────────┐
 │  Edge Agent   │  TLS  │  │  MQTT Broker │  │ Ingestion Worker  │    │   │  Next.js     │
 │ capture→infer │──────►│  │  (auth+TLS)  │─►│ validate→persist  │    │   │  Dashboard   │
 │ →event→buffer │       │  └─────────────┘   └───────┬──────────┘    │   │              │
 └───────────────┘       │                            ▼               │   │              │
                         │   ┌────────────┐   ┌────────────────┐      │   │              │
                         │   │ PostgreSQL │◄──┤  FastAPI API   │◄─────┼──►│  REST + WS   │
                         │   └────────────┘   │  REST + WS     │      │   └──────────────┘
                         │   ┌────────────┐   └────────────────┘      │
                         │   │ S3 storage │◄── snapshots               │
                         │   └────────────┘                            │
                         └──────────────────────────────────────────┘
```

### Technology Choices

| Concern | Choice | Rationale |
|---|---|---|
| Edge language | Python 3.11 | OpenCV, ONNX Runtime, paho-mqtt maturity |
| Inference | ONNX Runtime (CPU/INT8) | Portable across Pi/Jetson; quantization-friendly |
| Quantization | ONNX Runtime static quantization | Reproducible INT8 with calibration dataset |
| Frame capture | OpenCV (`cv2.VideoCapture`) | Standard, broad device support |
| Messaging | MQTT (paho-mqtt client; broker = EMQX/Mosquitto) | Lightweight, QoS, LWT, ideal for constrained links |
| Backend API | FastAPI + Uvicorn | Async, WebSockets, OpenAPI, fast |
| DB | PostgreSQL | Durable, relational fleet/event model, Render-managed |
| Object storage | S3-compatible (Render disk dev / S3 prod) | Snapshot blobs out of the DB |
| Migrations | Alembic | Versioned schema verify + migrate (Req 12.4) |
| Frontend | Next.js 14 (App Router) + TypeScript | Vercel-native, modern, SSR/ISR |
| Styling | Tailwind CSS + shadcn/ui + Framer Motion | Professional, consistent design system, not "AI slop" |
| Auth | JWT (PyJWT) + RBAC | Stateless, WS-compatible |
| Serialization | JSON (compact) with optional MessagePack | Compact wire format (Req 10.2) |

---

## Architecture

## Components and Interfaces

### Component: Edge Agent

The agent runs three cooperating loops in separate threads, coordinated through thread-safe shared state. This isolation satisfies Req 3.6 (capture + heartbeat keep running even if inference halts).

```
┌──────────────────────────────────────────────────────────┐
│                        Edge Agent                          │
│                                                            │
│  CaptureLoop ──► frame_buffer (latest frame, lock)         │
│       │                                                    │
│       ▼                                                    │
│  InferenceLoop ──► detections ──► EventFactory             │
│                                       │                    │
│                                       ▼                    │
│                              SnapshotEncoder               │
│                                       │                    │
│                                       ▼                    │
│  HeartbeatLoop ──────────────► MqttPublisher ──► Broker    │
│                                   │   ▲                    │
│                                   ▼   │                    │
│                              OutboxQueue (bounded, FIFO)   │
└──────────────────────────────────────────────────────────┘
```

Modules:
- `config.py` — env-driven config loader; fails fast on missing required vars, logging the exact names (Req 12.5).
- `camera.py` — `CameraSource`: open, read, health tracking, exponential-backoff reconnection (Req 1).
- `inference.py` — `Detector`: ONNX Runtime session, preprocessing, postprocessing (NMS), latency/FPS metrics, bounded auto-recovery (Req 3).
- `events.py` — `EventFactory`: builds detection events; applies confidence threshold and per-class debounce (Req 4, Req 10.3).
- `snapshot.py` — `SnapshotEncoder`: compress-to-fit JPEG with quality/downscale fallback (Req 4.5/4.6).
- `mqtt_client.py` — `MqttPublisher`: TLS + auth connect, QoS publish, LWT, bounded outbox, reconnect republish (Req 5).
- `health.py` — `HealthState`: status machine (`healthy`/`degraded`), metrics aggregation, idle handling (Req 11.4).
- `agent.py` — wiring + lifecycle.

#### Camera state machine (Req 1)

```
        start
          │
          ▼
     ┌─────────┐  read ok (N consecutive)   ┌──────────┐
     │ OPENING │ ─────────────────────────► │ HEALTHY  │
     └─────────┘                            └────┬─────┘
          ▲                                      │ read fails > threshold
          │ reconnect ok + N stable reads        ▼
     ┌──────────────────────┐  backoff      ┌──────────┐
     │ RECONNECTING(backoff)│ ◄──────────── │ DEGRADED │
     └──────────────────────┘               └──────────┘
```

`DEGRADED` persists until reconnect **and** `N` consecutive successful reads (Req 1.5/1.6). Read failures trigger the reconnect path even if the OS reports the device present (Req 1.7).

### Component: Quantization Toolchain

`tools/quantize.py` — CLI:
1. Load float32 ONNX (or convert from PyTorch/TF if provided).
2. Validate representative dataset exists and is readable; **fail fast** if missing/corrupt (Req 2.5).
3. Build a `CalibrationDataReader` over the representative dataset.
4. Run ONNX Runtime static quantization (QInt8).
5. Validate the output loads in ONNX Runtime (Req 2.6).
6. Evaluate accuracy delta vs float32 on a holdout; warn if `delta >= 5%` (Req 2.4).
7. Print size-reduction ratio + accuracy delta report (Req 2.3).

### Component: Cloud Backend (FastAPI)

```
backend/
  app/
    main.py            # FastAPI app, lifespan: migrate + start MQTT worker
    config.py          # env config, fail-fast
    db/
      models.py        # SQLAlchemy: Node, Event, Detection, User
      session.py
      migrations/      # Alembic
    ingestion/
      worker.py        # MQTT subscriber loop
      validators.py    # schema validation (Pydantic)
      offline_monitor.py # marks nodes offline (strict timeout, Req 6.6)
    api/
      auth.py          # JWT issue/verify, RBAC, 24h cap (Req 9.6)
      nodes.py         # fleet status
      events.py        # paginated/filterable events + signed snapshot URLs
      ws.py            # authenticated WebSocket hub
      health.py        # /healthz /readyz (Req 11.2)
    storage/
      object_store.py  # S3/disk abstraction, signed URLs
    services/
      event_bus.py     # in-process pub/sub: ingestion -> WS hub
```

Ingestion → WebSocket flow (Req 7.4/7.5): the ingestion worker persists an event, commits the transaction, **then** publishes to the in-process `event_bus`; the WS hub forwards to authenticated subscribers. No event ⇒ no push.

### Component: Operator Dashboard (Next.js)

```
frontend/
  app/
    layout.tsx           # theme, fonts, brand shell
    page.tsx             # Fleet overview
    nodes/[id]/page.tsx  # Node detail
    login/page.tsx
  components/
    brand/Logo.tsx       # placeholder mark until asset supplied (Req 8.7)
    Hero.tsx
    FleetSummary.tsx
    NodeCard.tsx
    EventFeed.tsx        # live WS feed
    EventCard.tsx
    Filters.tsx
    ui/ (shadcn)
  lib/
    api.ts               # REST client (JWT)
    ws.ts                # authenticated WS client w/ reconnect
    assets.ts            # asset resolver: real asset or placeholder
  styles/
    theme.css            # design tokens
```

---

## Design System & Branding (Req 8)

A restrained, enterprise-grade visual language inspired by major infrastructure/observability vendors — clarity over decoration, no gradients-for-the-sake-of-it, no "AI slop."

**Tokens**
- Palette: deep slate/near-black surfaces (`#0B0F14`, `#11161D`), cool neutral text (`#E6EAF0`), single accent (electric cyan `#22D3EE`) used sparingly for status/CTAs. Status colors: online `#34D399`, degraded `#FBBF24`, offline `#9CA3AF`/error `#F87171`.
- Typography: Geist / Inter for UI, JetBrains Mono for metrics.
- Spacing: 4px base scale; generous whitespace; 12px radii; subtle 1px borders over heavy shadows.
- Motion: Framer Motion micro-interactions (150–250ms ease-out); live items animate in subtly.

**Asset strategy (Req 8.7/8.8):** `lib/assets.ts` resolves each branded slot (logo, wordmark, hero, favicon) from `NEXT_PUBLIC_ASSET_*` env/config; if unset, renders a clean SVG placeholder consistent with the tokens. Supplying assets and rebuilding swaps them on next load.

> **Assets I need from you** (drop-in, I'll wire them up):
> 1. **Logo mark** — square SVG/PNG (≥512×512), transparent bg.
> 2. **Wordmark / full logo** — horizontal SVG/PNG (transparent).
> 3. **Favicon** — 32×32 + 512×512 (or one SVG).
> 4. **Hero image/illustration** — wide (≥1920×1080), dark-friendly; or I keep the generated abstract placeholder.
> 5. **Brand color** — if you have an exact hex, otherwise I use the cyan accent above.
> 6. Optional: product name/wordmark text if different from "Edge-Surveillance-Node".
> Until provided, professional placeholders render automatically.

---

## Data Models

### Wire schema — Detection Event (MQTT → JSON)
```json
{
  "schema_version": 1,
  "node_id": "node-abc123",
  "event_id": "uuid",
  "timestamp": "2026-06-30T12:00:00Z",
  "detections": [
    { "label": "person", "confidence": 0.92, "bbox": [x, y, w, h] }
  ],
  "snapshot": { "present": true, "format": "jpeg", "bytes": 48213, "omitted_reason": null },
  "metrics": { "inference_ms": 38.2, "fps": 11.4 }
}
```

### Wire schema — Heartbeat
```json
{
  "schema_version": 1,
  "node_id": "node-abc123",
  "timestamp": "2026-06-30T12:00:00Z",
  "status": "healthy",          // or "degraded"
  "metrics": { "fps": 11.4, "inference_ms": 38.2, "dropped_frames": 3,
               "queue_depth": 0, "connection": "connected", "state": "active" }
}
```

### Persistence (PostgreSQL)

- **nodes**: `node_id` (PK), `name`, `status`, `last_seen`, `first_seen`, `last_metrics` (jsonb).
- **events**: `event_id` (PK), `node_id` (FK), `timestamp`, `created_at`, `snapshot_ref` (nullable), `snapshot_omitted_reason`, `metrics` (jsonb).
- **detections**: `id` (PK), `event_id` (FK), `label`, `confidence`, `bbox` (jsonb).
- **users**: `id`, `email`, `password_hash`, `role` (`admin`|`viewer`), `created_at`.

MQTT topics: `nodes/{node_id}/events`, `nodes/{node_id}/heartbeat`, LWT on `nodes/{node_id}/status` (offline).

---

## API (selected)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | public | issue JWT (≤24h, Req 9.6) |
| GET | `/api/nodes` | viewer+ | fleet status (Req 7.1) |
| GET | `/api/nodes/{id}` | viewer+ | node detail + metrics |
| GET | `/api/events` | viewer+ | paginated/filterable events (Req 7.2) |
| GET | `/api/events/{id}/snapshot` | viewer+ | signed snapshot URL (Req 7.3) |
| WS | `/ws/events` | viewer+ (token) | live event push (Req 7.4/7.6) |
| GET | `/healthz`,`/readyz` | public | health/readiness (Req 11.2) |

---

## Correctness Properties

These invariants must hold across the system and are the basis for the test suite:

### Property 1: Degraded persistence
Once an edge node enters `degraded`, it never returns to `healthy` without a confirmed reconnect plus N consecutive successful frame reads.
**Validates: Requirements 1.5, 1.6**

### Property 2: No silent calibration
The quantization tool never produces an artifact when the representative dataset is missing or corrupt.
**Validates: Requirements 2.5**

### Property 3: Inference-failure containment
Any inference failure halts only the inference loop; capture and heartbeat loops keep running and the node keeps reporting.
**Validates: Requirements 3.4, 3.6**

### Property 4: Bounded recovery
Auto-recovery attempts are finite; after exhaustion the node stays degraded and never silently resumes.
**Validates: Requirements 3.5**

### Property 5: Confidence gate
No event is emitted for detections below the configured confidence threshold.
**Validates: Requirements 4.1**

### Property 6: Snapshot fit-or-flag
A transmitted snapshot is always within the size limit; if omitted, the event carries an explicit omission flag.
**Validates: Requirements 4.6**

### Property 7: Republish discipline
Queued events are republished only after a genuine disconnect with a non-empty queue; never otherwise.
**Validates: Requirements 5.4, 5.5**

### Property 8: Strict offline
A node is offline only when `now - last_seen > timeout` (strictly greater), never at the exact last-seen instant.
**Validates: Requirements 6.6**

### Property 9: Commit-before-push
A WebSocket push for an event occurs only after that event is durably committed, within 2s, and never without a real event.
**Validates: Requirements 7.4, 7.5**

### Property 10: Auth-before-data
No protected REST/WS data is delivered without a valid JWT; the broker never accepts unauthenticated connections.
**Validates: Requirements 9.1, 9.2**

### Property 11: JWT cap
Configured JWT lifetime never exceeds 24h; over-limit configuration is rejected, not clamped.
**Validates: Requirements 9.6**

### Property 12: Fail-fast config
A component with a missing required env var logs the exact name and exits non-zero; it never runs partially configured.
**Validates: Requirements 12.5**

## Error Handling

| Scenario | Behavior | Req |
|---|---|---|
| Single frame read fail | warn + continue | 1.3 |
| Sustained camera failure | degraded + backoff reconnect | 1.4–1.7 |
| Missing/corrupt calibration data | fail fast, clear error | 2.5 |
| Model load / inference failure | log, degraded heartbeat, halt loop, bounded auto-recover, then manual | 3.4/3.5 |
| Snapshot over size limit | reduce quality/downscale; omit w/ flag as last resort | 4.6 |
| Broker disconnect | bounded FIFO outbox; republish on real reconnect | 5.3–5.5 |
| Malformed MQTT message | reject + structured log | 6.2 |
| Missing env var | log exact name + exit non-zero | 12.5 |
| Over-limit JWT lifetime config | reject with validation error | 9.6 |
| Failed broker auth | reject connection, never accept anon | 9.2 |

---

## Testing Strategy

- **Edge unit tests:** camera state machine (mock VideoCapture), confidence threshold + debounce, snapshot compress-to-fit, outbox FIFO + republish-only-on-reconnect, config fail-fast.
- **Quantization tests:** fail-fast on bad dataset, accuracy-delta boundary (==5% warns), output-loads validation.
- **Backend unit tests:** schema validation, offline strict-inequality timeout, JWT 24h cap rejection, RBAC, signed URL generation, ingestion→WS only-on-commit.
- **Integration:** docker-compose (broker + postgres + minio + backend); agent publishes → event appears via API + WS within 2s.
- **Frontend:** component tests (placeholder vs real asset resolution, responsive 360–1920), WS live-update, auth guard.
- **CI:** lint + typecheck + unit on PR.

---

## Deployment

**Render (backend):** Web Service (FastAPI/Uvicorn) + Background Worker (MQTT ingestion) OR combined via lifespan; managed PostgreSQL; managed/managed-disk object storage (S3 in prod). Health check `/healthz`. Alembic migrations run on startup (Req 12.4). MQTT broker: managed EMQX/HiveMQ Cloud or a Render private service with TLS + auth.

**Vercel (frontend):** Next.js build; env `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_ASSET_*`.

**Edge:** Dockerfile (ARM-compatible) or systemd unit; `.env` for broker creds, node ID, model path.

All secrets via environment; nothing committed. `.env.example` documents every variable.

