<div align="center">

# Edge-Surveillance-Node

**Quantized on-device object detection, event-driven MQTT telemetry, and a real-time operator dashboard for constrained edge hardware.**

[![Backend CI](https://img.shields.io/badge/backend-pytest-3BE66B)](#testing)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-000)](#stack)
[![Edge](https://img.shields.io/badge/edge-ONNX%20INT8-1C7A3D)](#stack)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey)](#license)

</div>

---

Edge-Surveillance-Node turns a Raspberry Pi or Jetson Nano into an intelligent camera node. It captures frames with OpenCV, runs a quantized INT8 ONNX detection model on-device, and publishes lightweight detection events over MQTT to a cloud service. Operators monitor the whole fleet through a modern, real-time web console.

It is engineered around three constraints that shape every design decision:

- **Constrained compute** — models are quantized to INT8 so they run at usable frame rates on weak hardware.
- **Constrained bandwidth** — nodes transmit event-driven metadata and size-bounded JPEG snapshots, never a 24/7 video stream.
- **Constrained connectivity** — nodes buffer, reconnect, and recover gracefully across unreliable links.

## Highlights

- **On-device inference** — ONNX Runtime with INT8 models; NMS, per-class debounce, and confidence gating happen at the edge.
- **Reproducible quantization toolchain** — static INT8 quantization with representative-dataset calibration, output validation, and an accuracy-delta report.
- **Resilient telemetry** — TLS-authenticated MQTT with a stable client ID, Last Will, a bounded FIFO outbox, and replay-on-reconnect.
- **Real-time backend** — FastAPI ingestion worker, PostgreSQL persistence, S3-compatible snapshot storage, and an authenticated WebSocket hub that pushes detections within ~2 seconds of commit.
- **Operator dashboard** — Next.js 14 console with a live event feed, fleet health, per-node drill-down, and an analytics tab with CSV/JSON export.
- **Secure by default** — JWT auth with RBAC and a hard 24h token cap, TLS everywhere, fail-fast configuration, and no anonymous broker access.

## Architecture

```
 Edge Hardware                Cloud (Render)                         Vercel
┌──────────────┐   MQTT/TLS  ┌──────────────┐  ┌────────────────┐   ┌──────────────┐
│  Edge Agent  │ ──────────► │  MQTT Broker │─►│  Ingestion     │   │  Next.js     │
│  capture →   │   auth      │  (auth+TLS)  │  │  worker        │   │  Dashboard   │
│  infer →     │             └──────────────┘  └───────┬────────┘   │              │
│  event →     │                                       ▼            │  REST + WSS  │
│  buffer      │             ┌──────────────┐  ┌────────────────┐   │              │
└──────────────┘             │ PostgreSQL   │◄─┤  FastAPI API   │◄──┤              │
                             │ + S3 storage │  │  REST + WS     │   └──────────────┘
                             └──────────────┘  └────────────────┘
```

The edge agent runs three cooperating threads — capture, inference, and heartbeat — so the node stays observable even if inference halts. The backend persists each event, then fans it out to subscribed dashboards over WebSocket.

## Stack

| Layer | Technology |
|---|---|
| Edge agent | Python 3.11, OpenCV, ONNX Runtime, paho-mqtt |
| Quantization | ONNX Runtime static quantization (QInt8) |
| Backend | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, PyJWT, boto3 |
| Messaging | MQTT (Mosquitto / EMQX), TLS + auth |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion |
| Charts | Hand-built SVG (donut, gauge, line, bars) — no chart dependency |
| Deploy | Render (backend), Vercel (frontend) |

## Repository layout

| Path | Description |
|---|---|
| `edge/` | On-device agent: capture, inference, event generation, MQTT publishing |
| `backend/` | FastAPI service: ingestion, REST + WebSocket API, persistence, storage |
| `frontend/` | Next.js operator dashboard |
| `tools/` | Model quantization toolchain and a demo MQTT publisher |
| `infra/` | docker-compose stack, Mosquitto config, Render blueprint |
| `docs/` | Deployment guide |

## Quick start (local)

Requires Docker, Python 3.11+, and Node 20+.

```bash
# 1. Broker (Mosquitto with auth) — generate credentials then start it
cd infra
./mosquitto/gen-passwd.ps1        # or gen-passwd.sh on macOS/Linux
docker compose up -d broker

# 2. Backend (SQLite + disk storage for zero-friction local dev)
cd ../backend
pip install -r requirements.txt
cp .env.example .env
python seed.py --email admin@example.com --password admin --role admin
uvicorn asgi:app --host 127.0.0.1 --port 8000

# 3. Frontend
cd ../frontend
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:3000

# 4. Simulate an edge node (no camera/model needed)
cd ../tools
python demo_publisher.py --node-id node-demo-01 --events 30 --interval 2
```

Sign in at the dashboard with the seeded credentials and watch detections stream in live.

For a full broker + Postgres + MinIO + backend stack, run `docker compose up -d` from `infra/` (see [`infra/README.md`](infra/README.md)).

## Running an edge agent

Produce a quantized model, then point the agent at it:

```bash
# Quantize a float32 ONNX model to INT8
cd tools
python quantize.py --source models/detector.fp32.onnx \
                   --output models/detector.int8.onnx \
                   --dataset data/calibration_images/

# Run the agent
cd ../edge
pip install -r requirements.txt
cp .env.example .env              # set NODE_ID, MODEL_PATH, MQTT_* credentials
python -m src.agent
```

## Testing

```bash
cd edge     && pytest      # capture state machine, inference, events, MQTT outbox
cd backend  && pytest      # auth, ingestion, offline detection, API, WS, analytics, e2e
cd tools    && pytest      # quantization fail-fast and reporting
cd frontend && npm test    # asset resolution, components, utilities
```

## Deployment

The backend deploys to **Render** (web service + managed PostgreSQL) and the frontend to **Vercel**. An MQTT broker and S3-compatible bucket are provisioned separately. Full instructions, environment variables, and a smoke test are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). A Render blueprint is provided at [`infra/render.yaml`](infra/render.yaml).

## Security

- JWT authentication on all protected REST and WebSocket access; tokens are hard-capped at 24 hours.
- Role-based access control (`admin`, `viewer`).
- TLS for broker and API traffic; the broker rejects unauthenticated connections.
- All secrets are supplied via environment variables and never committed.
- Components fail fast on missing required configuration.

## Specification

The product is built from a structured spec under [`.kiro/specs/edge-surveillance-node/`](.kiro/specs/edge-surveillance-node) covering requirements, design, correctness properties, and the task plan.

## License

Proprietary. All rights reserved.
