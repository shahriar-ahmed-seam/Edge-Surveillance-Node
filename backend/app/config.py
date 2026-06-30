"""Backend configuration with fail-fast validation."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

logger = logging.getLogger("backend.config")

MAX_JWT_LIFETIME_HOURS = 24  # hard cap

_MISSING = object()


class ConfigError(Exception):
    pass


def _get(name: str, default=_MISSING, cast: Callable = str):
    raw = os.environ.get(name, _MISSING)
    if raw is _MISSING:
        return default
    try:
        return cast(raw)
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"Invalid value for {name!r}: {raw!r} ({exc})") from exc


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_lifetime_hours: int
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_use_tls: bool
    mqtt_ca_cert: str
    mqtt_topic_events: str
    mqtt_topic_heartbeat: str
    storage_backend: str
    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    signed_url_ttl_seconds: int
    disk_storage_path: str
    node_offline_timeout_s: float
    offline_check_interval_s: float
    host: str
    port: int
    cors_allow_origins: List[str]
    log_level: str


def load_settings(*, exit_on_error: bool = True) -> Settings:
    missing: List[str] = []

    def required(name: str, cast: Callable = str):
        value = _get(name, cast=cast)
        if value is _MISSING:
            missing.append(name)
            return None
        return value

    jwt_lifetime = _get("JWT_LIFETIME_HOURS", 12, int)
    storage_backend = _get("STORAGE_BACKEND", "s3")

    candidate = dict(
        database_url=required("DATABASE_URL"),
        jwt_secret=required("JWT_SECRET"),
        jwt_algorithm=_get("JWT_ALGORITHM", "HS256"),
        jwt_lifetime_hours=jwt_lifetime,
        mqtt_host=required("MQTT_HOST"),
        mqtt_port=_get("MQTT_PORT", 8883, int),
        mqtt_username=required("MQTT_USERNAME"),
        mqtt_password=required("MQTT_PASSWORD"),
        mqtt_use_tls=_get("MQTT_USE_TLS", True, _as_bool),
        mqtt_ca_cert=_get("MQTT_CA_CERT", ""),
        mqtt_topic_events=_get("MQTT_TOPIC_EVENTS", "nodes/+/events"),
        mqtt_topic_heartbeat=_get("MQTT_TOPIC_HEARTBEAT", "nodes/+/heartbeat"),
        storage_backend=storage_backend,
        s3_endpoint_url=_get("S3_ENDPOINT_URL", ""),
        s3_bucket=_get("S3_BUCKET", "snapshots"),
        s3_access_key=_get("S3_ACCESS_KEY", ""),
        s3_secret_key=_get("S3_SECRET_KEY", ""),
        s3_region=_get("S3_REGION", "us-east-1"),
        signed_url_ttl_seconds=_get("SIGNED_URL_TTL_SECONDS", 300, int),
        disk_storage_path=_get("DISK_STORAGE_PATH", "./data/snapshots"),
        node_offline_timeout_s=_get("NODE_OFFLINE_TIMEOUT_S", 30.0, float),
        offline_check_interval_s=_get("OFFLINE_CHECK_INTERVAL_S", 5.0, float),
        host=_get("HOST", "0.0.0.0"),
        port=_get("PORT", 8000, int),
        cors_allow_origins=[
            o.strip() for o in _get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",") if o.strip()
        ],
        log_level=_get("LOG_LEVEL", "INFO"),
    )

    errors: List[str] = []
    if missing:
        errors.append("Missing required environment variable(s): " + ", ".join(sorted(missing)))

    # JWT lifetime cap is rejected, not clamped.
    if jwt_lifetime is not _MISSING and jwt_lifetime > MAX_JWT_LIFETIME_HOURS:
        errors.append(
            f"JWT_LIFETIME_HOURS={jwt_lifetime} exceeds the maximum of {MAX_JWT_LIFETIME_HOURS}h"
        )

    if errors:
        msg = "; ".join(errors)
        logger.error(msg)
        if exit_on_error:
            sys.stderr.write(msg + "\n")
            sys.exit(1)
        raise ConfigError(msg)

    return Settings(**candidate)  # type: ignore[arg-type]
