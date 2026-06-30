# Local Infrastructure (docker-compose)

Brings up the full backend stack for local end-to-end testing:

- **broker** — Mosquitto MQTT broker with authentication required (anonymous denied)
- **postgres** — PostgreSQL 16
- **minio** — S3-compatible object storage for snapshots
- **backend** — FastAPI ingestion + API + WebSocket service

## One-time setup

Generate the broker password file (hashed credentials):

```powershell
# Windows
./mosquitto/gen-passwd.ps1
```

```bash
# macOS / Linux
chmod +x mosquitto/gen-passwd.sh && ./mosquitto/gen-passwd.sh
```

This creates users `edge` / `edge-secret` and `ingestion` / `ingestion-secret`.

## Run

```bash
docker compose up -d
docker compose logs -f backend
```

Then seed an admin user:

```bash
docker compose exec backend python seed.py --email admin@example.com --password admin --role admin
```

- API:        http://localhost:8000  (`/healthz`, `/docs`)
- MinIO UI:    http://localhost:9001  (minioadmin / minioadmin)
- Broker:      mqtt://localhost:1883

## Security note

`allow_anonymous false` ensures the broker rejects unauthenticated connections
and any client presenting invalid credentials (Requirement 9.2). For production,
enable the TLS listener on 8883 (see `mosquitto/mosquitto.conf`) and use managed
secrets — never commit real credentials.
