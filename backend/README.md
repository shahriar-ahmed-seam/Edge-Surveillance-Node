# Backend

FastAPI service for Edge-Surveillance-Node. Combines MQTT ingestion, a REST +
WebSocket API, PostgreSQL persistence, and S3-compatible snapshot storage.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env          # edit values
python seed.py --email admin@example.com --password admin --role admin
uvicorn asgi:app --reload
```

Or bring up the whole stack with docker-compose — see [`../infra/README.md`](../infra/README.md).

## Layout

```
app/
  config.py            # env config, fail-fast, JWT 24h cap
  db/                  # SQLAlchemy models, session, Alembic migrations
  api/                 # auth, nodes, events, ws, health routes
  ingestion/           # MQTT worker, validators, offline monitor
  services/event_bus.py# ingestion -> WebSocket fan-out
  storage/             # S3 / disk object store + signed URLs
  main.py              # app factory + lifespan
asgi.py                # production entry point (uvicorn asgi:app)
seed.py                # create/update users
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Key behaviors

- Migrations apply automatically on startup; existing schemas are verified and
  pending migrations applied (never blindly skipped).
- Missing required env vars are logged by name and the process exits (fail fast).
- JWT lifetime over 24h is rejected at startup, not silently clamped.
- Nodes are marked offline only when `now - last_seen > timeout` (strict).
- WebSocket pushes happen only after an event is committed, and never without a
  real detection.
