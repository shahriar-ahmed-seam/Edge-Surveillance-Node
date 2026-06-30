# Implementation Plan — Edge-Surveillance-Node

## Overview

This plan implements Edge-Surveillance-Node in dependency order: shared scaffolding first, then the edge agent (config → capture → quantization → inference → events → MQTT → wiring), then the backend (foundation → auth → ingestion → API/WS), then the dashboard, and finally integration, E2E verification, and Render/Vercel deployment configuration. Each task is incremental, test-backed, and traces to specific requirements.

## Task Dependency Graph

```
1 (scaffolding)
├── 2 (edge config) ──► 3 (camera) ─┐
│                                   ├──► 8 (health + agent wiring)
├── 4 (quantization) ──► 5 (inference) ─┤
│                        6 (events/snapshot) ─┤
│                        7 (mqtt) ────────────┘
│
├── 9 (backend foundation) ──► 10 (auth)
│                          └─► 11 (ingestion) ──► 12 (API + WS)
│
└── 13 (dashboard foundation) ──► 14 (dashboard views)
                                          │
8, 12, 14 ───────────────────────────────► 15 (integration + deploy)
```

- Tasks 2–8 (edge), 9–12 (backend), and 13–14 (frontend) are largely independent tracks after task 1.
- Task 15 depends on the edge agent (8), backend API/WS (12), and dashboard (14) being complete.

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"], "dependsOn": [] },
    { "wave": 2, "tasks": ["2", "4", "9", "13"], "dependsOn": ["1"] },
    { "wave": 3, "tasks": ["3", "5", "6", "7", "10", "11"], "dependsOn": ["2", "4", "9"] },
    { "wave": 4, "tasks": ["8", "12", "14"], "dependsOn": ["3", "5", "6", "7", "10", "11", "13"] },
    { "wave": 5, "tasks": ["15"], "dependsOn": ["8", "12", "14"] }
  ]
}
```


## Tasks

- [x] 1. Establish monorepo scaffolding and shared conventions
  - Create `edge/`, `backend/`, `frontend/`, `tools/`, `infra/` directories with READMEs
  - Add root `.gitignore`, `.editorconfig`, and a top-level `README.md` describing the architecture
  - Add `.env.example` files for edge, backend, and frontend documenting every variable
  - _Requirements: 12.1, 12.2, 12.3, 9.5_

- [x] 2. Implement edge configuration loader with fail-fast validation
  - [x] 2.1 Create `edge/src/config.py` loading all settings from environment with safe defaults
    - Define required vs optional variables; on missing required vars, log exact names and exit non-zero
    - _Requirements: 12.1, 12.5_
  - [x] 2.2 Write unit tests for fail-fast behavior and default resolution
    - _Requirements: 12.5_

- [x] 3. Implement camera capture with lifecycle state machine
  - [x] 3.1 Create `edge/src/camera.py` (`CameraSource`) with OpenCV capture loop and latest-frame buffer
    - Target FPS loop; per-frame failure logs warning and continues
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 3.2 Add health tracking + exponential-backoff reconnection state machine
    - Enter degraded after failure threshold; trigger reconnect even when device reports present
    - Clear degraded only after reconnect + N consecutive successful reads
    - _Requirements: 1.4, 1.5, 1.6, 1.7_
  - [x] 3.3 Write unit tests with a mocked VideoCapture covering all transitions
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 4. Build the quantization toolchain
  - [x] 4.1 Create `tools/quantize.py` CLI: load float32 ONNX, calibrate, static INT8 quantize
    - Fail fast if representative dataset missing/corrupt (no default calibration)
    - _Requirements: 2.1, 2.2, 2.5_
  - [x] 4.2 Add output validation (loads in ONNX Runtime), size-ratio + accuracy-delta report
    - Emit warning when accuracy delta >= 5% (boundary inclusive)
    - _Requirements: 2.3, 2.4, 2.6_
  - [x] 4.3 Write tests for fail-fast, 5% boundary warning, and output-loads validation
    - _Requirements: 2.4, 2.5, 2.6_

- [x] 5. Implement edge inference engine
  - [x] 5.1 Create `edge/src/inference.py` (`Detector`): ONNX Runtime session, preprocess, postprocess (NMS)
    - Produce detections with labels, confidence, bbox; record latency/FPS
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 5.2 Add failure handling: log, degraded heartbeat signal, halt loop; bounded backoff auto-recovery then manual
    - Ensure any inference failure (not just load) enters this path
    - _Requirements: 3.4, 3.5, 3.6_
  - [x] 5.3 Write tests for load failure, runtime inference failure, and bounded recovery exhaustion
    - _Requirements: 3.4, 3.5_

- [x] 6. Implement detection event generation and snapshot handling
  - [x] 6.1 Create `edge/src/events.py` (`EventFactory`) applying confidence threshold and per-class debounce
    - Build event payload with node_id, UTC ISO-8601 timestamp, detections, metrics
    - _Requirements: 4.1, 4.2, 10.3_
  - [x] 6.2 Create `edge/src/snapshot.py` (`SnapshotEncoder`): JPEG compress-to-fit (quality + downscale fallback)
    - Respect max byte size; omit with flag only as last resort
    - _Requirements: 4.3, 4.4, 4.5, 4.6_
  - [x] 6.3 Write tests for threshold suppression, debounce, and compress-to-fit/omit-flag logic
    - _Requirements: 4.1, 4.6, 10.3_

- [x] 7. Implement MQTT publisher with buffering and recovery
  - [x] 7.1 Create `edge/src/mqtt_client.py` (`MqttPublisher`): TLS + authenticated connect, QoS publish, stable client ID, LWT
    - _Requirements: 5.1, 5.2, 5.6, 9.1, 9.3_
  - [x] 7.2 Add bounded FIFO outbox; on real reconnect with non-empty queue, republish in order
    - Never republish without a genuine disconnect or with an empty queue; drop-oldest with logged metric when full
    - _Requirements: 5.3, 5.4, 5.5_
  - [x] 7.3 Write tests for outbox bounding, drop-oldest, and republish-only-on-reconnect
    - _Requirements: 5.3, 5.4, 5.5_

- [x] 8. Implement edge health state and bandwidth optimization, then wire the agent
  - [x] 8.1 Create `edge/src/health.py` (`HealthState`): healthy/degraded machine, metric aggregation, idle handling (skip zeros, report idle)
    - _Requirements: 11.1, 11.4, 1.5_
  - [x] 8.2 Enforce event-driven transmission (heartbeats only when idle) and compact serialization
    - _Requirements: 10.1, 10.2, 10.4_
  - [x] 8.3 Create `edge/src/agent.py` wiring capture, inference, events, mqtt, heartbeat loops in isolated threads
    - Ensure capture + heartbeat continue while inference halted
    - _Requirements: 3.6, 11.1_
  - [x] 8.4 Add `edge/Dockerfile` (ARM-compatible) and run instructions
    - _Requirements: 12.1, 12.3_

- [x] 9. Stand up backend foundation: config, DB models, migrations
  - [x] 9.1 Create `backend/app/config.py` with env loading + fail-fast on missing required vars
    - _Requirements: 12.1, 12.5_
  - [x] 9.2 Define SQLAlchemy models (nodes, events, detections, users) and session setup
    - _Requirements: 6.3, 6.4_
  - [x] 9.3 Configure Alembic: auto-apply schema when absent; verify + apply pending migrations when present
    - _Requirements: 12.4_
  - [x] 9.4 Write tests for config fail-fast and migration apply/verify logic
    - _Requirements: 12.4, 12.5_

- [x] 10. Implement authentication, authorization, and security
  - [x] 10.1 Create `backend/app/api/auth.py`: password hashing, JWT issue/verify, RBAC dependency
    - Cap JWT lifetime at 24h; reject over-limit configuration with a validation error
    - _Requirements: 9.1, 9.4, 9.6_
  - [x] 10.2 Add TLS/secure-config conventions and ensure secrets only via env
    - _Requirements: 9.3, 9.5_
  - [x] 10.3 Write tests for JWT cap rejection, RBAC enforcement, and auth failure paths
    - _Requirements: 9.1, 9.4, 9.6_

- [x] 11. Implement ingestion worker and fleet state
  - [x] 11.1 Create `backend/app/ingestion/validators.py` (Pydantic schemas) for events and heartbeats
    - Reject malformed messages with structured logs
    - _Requirements: 6.2_
  - [x] 11.2 Create `backend/app/ingestion/worker.py`: subscribe to topics, validate, persist events, store snapshots by reference
    - _Requirements: 6.1, 6.2, 6.3, 6.5_
  - [x] 11.3 Update node last-seen/status on heartbeat; implement offline monitor with strict `now - last_seen > timeout`
    - _Requirements: 6.4, 6.6_
  - [x] 11.4 Create `backend/app/storage/object_store.py` (S3/disk) with signed URL generation
    - _Requirements: 6.5, 7.3_
  - [x] 11.5 Write tests for validation rejection, strict offline timeout, and snapshot reference persistence
    - _Requirements: 6.2, 6.5, 6.6_

- [x] 12. Implement REST API and real-time WebSocket push
  - [x] 12.1 Create `backend/app/api/nodes.py` and `events.py`: fleet status, paginated/filterable events, signed snapshot URLs
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 12.2 Create in-process `event_bus` and `backend/app/api/ws.py`: authenticated WS hub
    - Push only after event is committed to storage; within 2s; never push without a real event
    - _Requirements: 7.4, 7.5, 7.6_
  - [x] 12.3 Add `backend/app/api/health.py` (`/healthz`, `/readyz`) and structured logging setup
    - _Requirements: 11.2, 11.3_
  - [x] 12.4 Wire `backend/app/main.py` lifespan: run migrations, start ingestion worker, mount routes/WS
    - _Requirements: 6.1, 12.4_
  - [x] 12.5 Write tests for events pagination/filtering, WS auth gate, and commit-before-push ordering
    - _Requirements: 7.2, 7.4, 7.5, 7.6_

- [x] 13. Build the dashboard foundation and design system
  - [x] 13.1 Scaffold Next.js 14 (App Router, TS) with Tailwind, shadcn/ui, Framer Motion; define theme tokens
    - _Requirements: 8.1, 12.2_
  - [x] 13.2 Create `lib/assets.ts` asset resolver and `components/brand/Logo.tsx` + `Hero.tsx` with professional placeholders
    - Use real assets when env-provided; placeholders otherwise; apply on next load
    - _Requirements: 8.7, 8.8_
  - [x] 13.3 Create `lib/api.ts` (JWT REST client) and `lib/ws.ts` (authenticated WS with reconnect)
    - _Requirements: 7.1, 7.6, 9.1_
  - [x] 13.4 Implement login page and auth guard/session handling
    - _Requirements: 9.1_

- [x] 14. Build dashboard views and live updates
  - [x] 14.1 Implement fleet overview (`app/page.tsx`): summary counts + recent events + node cards
    - _Requirements: 8.1_
  - [x] 14.2 Implement node detail (`app/nodes/[id]/page.tsx`): status history, FPS/latency metrics, recent detections
    - _Requirements: 8.2_
  - [x] 14.3 Implement live `EventFeed`/`EventCard` updating via WebSocket without full reload; show snapshot, classes, confidence, local-time timestamp
    - _Requirements: 8.3, 8.4_
  - [x] 14.4 Implement `Filters` (node, class, time range) and responsive layout 360–1920 with graceful sub-360 rendering
    - _Requirements: 8.5, 8.6_
  - [x] 14.5 Write frontend tests for asset resolution, WS live update, auth guard, and responsiveness
    - _Requirements: 8.3, 8.6, 8.7_

- [x] 15. Integration, end-to-end verification, and deployment configuration
  - [x] 15.1 Create `infra/docker-compose.yml` (broker with auth+TLS, postgres, minio, backend) for local E2E
    - _Requirements: 5.1, 6.1, 9.2, 9.3_
  - [x] 15.2 Add broker auth config asserting failed auth rejects connection and no anonymous access
    - _Requirements: 9.2_
  - [x] 15.3 Write an E2E test: agent publishes a detection → event retrievable via REST and pushed via WS within 2s
    - _Requirements: 7.4, 5.4_
  - [x] 15.4 Add `render.yaml` (backend web + worker + postgres + health checks) and Vercel project config + env docs
    - _Requirements: 11.2, 12.2, 12.3_
  - [x] 15.5 Add root README deployment guide (Render + Vercel + edge) and finalize all `.env.example` files
    - _Requirements: 12.1, 12.2, 12.3, 9.5_

## Notes

- All secrets (broker credentials, JWT signing key, DB URL, S3 credentials) are provided exclusively via environment variables and documented in `.env.example` files; nothing is committed.
- Branded visual assets (logo mark, wordmark, favicon, hero, brand hex) are pending from the operator. Until supplied, the dashboard renders professional neutral placeholders; assets apply on next build/load.
- Tests are written alongside each component (not deferred) per the design's testing strategy. Property invariants in the design's Correctness Properties section are the acceptance basis.
- Deployment targets: backend → Render (web + worker + managed PostgreSQL + object storage), frontend → Vercel. MQTT broker runs as a managed service or Render private service with TLS + auth.

