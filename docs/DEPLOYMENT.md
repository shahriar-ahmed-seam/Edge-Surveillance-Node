# Deployment Guide

Edge-Surveillance-Node deploys as three independently-operated pieces:

1. **Backend** → Render (FastAPI: REST + WebSocket + MQTT ingestion)
2. **Frontend** → Vercel (Next.js dashboard)
3. **Edge agent** → your hardware (Raspberry Pi / Jetson Nano)
4. **MQTT broker** → a managed broker with TLS + auth (EMQX Cloud / HiveMQ Cloud)
5. **Object storage** → an S3-compatible bucket for snapshots

```
 Edge agent ──MQTT/TLS──► Broker ──► Render backend ──► Postgres + S3
                                          ▲
                                          │ REST + WSS
                                     Vercel frontend
```

---

## 1. MQTT broker

Provision a managed MQTT broker with TLS (port 8883) and authentication. Create
two credentials:

- `edge` — used by edge agents to publish
- `ingestion` — used by the backend to subscribe

Disable anonymous access. Failed authentication must reject the connection
(Requirement 9.2).

## 2. Object storage

Create an S3-compatible bucket (AWS S3, Cloudflare R2, Backblaze B2, etc.) and an
access key/secret with read+write on the bucket. Note the endpoint URL, bucket
name, and region.

## 3. Backend on Render

Option A — Blueprint (recommended): commit `infra/render.yaml` and create a new
Blueprint instance in Render pointing at the repo. It provisions the web service
and a managed PostgreSQL database.

Option B — Manual: create a Web Service from the `backend/` directory using its
`Dockerfile`, and add a managed PostgreSQL instance.

Set these environment variables (secrets via Render's secret store):

| Variable | Value |
|---|---|
| `DATABASE_URL` | from the managed Postgres (use the `postgresql+psycopg://` scheme) |
| `JWT_SECRET` | long random string |
| `JWT_LIFETIME_HOURS` | `12` (max 24; larger is rejected at startup) |
| `MQTT_HOST` / `MQTT_PORT` | broker host / `8883` |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | `ingestion` credentials |
| `MQTT_USE_TLS` | `true` |
| `STORAGE_BACKEND` | `s3` |
| `S3_ENDPOINT_URL` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_REGION` | bucket details |
| `CORS_ALLOW_ORIGINS` | your Vercel URL, e.g. `https://your-app.vercel.app` |

Health check path: `/healthz`. Migrations run automatically on startup
(Requirement 12.4). After first deploy, seed an admin user from the Render shell:

```bash
python seed.py --email admin@yourco.com --password '<strong-password>' --role admin
```

> If `DATABASE_URL` uses the bare `postgresql://` scheme, change it to
> `postgresql+psycopg://` so SQLAlchemy uses the psycopg 3 driver.

## 4. Frontend on Vercel

Import the repo into Vercel and set the **Root Directory** to `frontend/`.
Framework preset: Next.js. Set environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://esn-backend.onrender.com` |
| `NEXT_PUBLIC_WS_URL` | `wss://esn-backend.onrender.com/ws/events` |
| `NEXT_PUBLIC_BRAND_NAME` | your product name (optional) |
| `NEXT_PUBLIC_ASSET_LOGO` / `_WORDMARK` / `_HERO` / `_FAVICON` | asset URLs once supplied |
| `NEXT_PUBLIC_BRAND_ACCENT` | brand hex (optional) |

Deploy. Until brand assets are configured, the dashboard renders professional
placeholders; setting the asset variables and redeploying swaps them in.

## 5. Edge agent

On each device:

```bash
cd edge
cp .env.example .env   # fill in NODE_ID, MODEL_PATH, MQTT_* (edge credentials)
pip install -r requirements.txt
python -m src.agent
```

Or via Docker:

```bash
docker build -t esn-agent ./edge
docker run -d --restart unless-stopped \
  --env-file edge/.env \
  --device /dev/video0 \
  -v $PWD/models:/app/models \
  esn-agent
```

Produce the quantized model first with the toolchain (`tools/quantize.py`) and
place it at the path referenced by `MODEL_PATH`.

---

## Smoke test after deploy

1. `GET https://<backend>/healthz` → `{"status":"ok"}`
2. Log in to the dashboard with the seeded admin user.
3. Start an edge agent; within one heartbeat interval it should appear in the
   fleet view as online.
4. Trigger a detection; it should appear live in the event feed within ~2s.
