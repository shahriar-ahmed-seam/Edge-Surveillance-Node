"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analytics, auth_routes, events, health, nodes, ws
from .config import load_settings
from .db.schema import apply_schema
from .db.session import init_engine
from .ingestion.offline_monitor import OfflineMonitor
from .ingestion.worker import IngestionWorker
from .logging_config import configure_logging
from .services.event_bus import EventBus
from .storage.object_store import build_object_store

logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    # 1. DB + schema
    init_engine(settings.database_url)
    apply_schema(settings.database_url)

    # 2. Object storage
    app.state.object_store = build_object_store(settings)

    # 3. Event bus bound to the running loop (for threadsafe publish from worker)
    bus: EventBus = app.state.event_bus
    bus.bind_loop(asyncio.get_running_loop())

    # 4. Ingestion worker + offline monitor
    worker = IngestionWorker(settings, app.state.object_store, bus)
    monitor = OfflineMonitor(settings)
    try:
        worker.start()
    except Exception as exc:
        logger.error("Ingestion worker failed to start: %s", exc)
    monitor.start()
    app.state.worker = worker
    app.state.monitor = monitor

    logger.info("Backend started")
    try:
        yield
    finally:
        worker.stop()
        monitor.stop()
        logger.info("Backend stopped")


def create_app(settings=None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Edge-Surveillance-Node API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.event_bus = EventBus()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth_routes.router)
    app.include_router(nodes.router)
    app.include_router(events.router)
    app.include_router(analytics.router)
    app.include_router(ws.router)
    return app


app = None


def get_app() -> FastAPI:
    global app
    if app is None:
        app = create_app()
    return app


if __name__ == "__main__":
    import uvicorn

    _settings = load_settings()
    application = create_app(_settings)
    uvicorn.run(application, host=_settings.host, port=_settings.port)
