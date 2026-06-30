"""Environment-driven configuration with fail-fast validation."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, List

try:  # dotenv is convenient locally but optional in production
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is best-effort
    pass

logger = logging.getLogger("edge.config")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


_MISSING = object()


def _get(name: str, default=_MISSING, cast: Callable = str):
    raw = os.environ.get(name, _MISSING)
    if raw is _MISSING:
        if default is _MISSING:
            return _MISSING  # sentinel collected by the loader for fail-fast
        return default
    try:
        return cast(raw)
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"Invalid value for {name!r}: {raw!r} ({exc})") from exc


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EdgeConfig:
    # identity
    node_id: str
    node_name: str
    # camera
    camera_source: str
    target_fps: float
    camera_failure_threshold: int
    camera_recovery_reads: int
    camera_backoff_base_s: float
    camera_backoff_max_s: float
    # model / inference
    model_path: str
    model_labels_path: str
    model_input_size: int
    confidence_threshold: float
    nms_iou_threshold: float
    inference_max_recovery_attempts: int
    # events / snapshots
    event_debounce_seconds: float
    snapshot_enabled: bool
    snapshot_max_bytes: int
    snapshot_min_jpeg_quality: int
    # mqtt
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_use_tls: bool
    mqtt_ca_cert: str
    mqtt_qos: int
    outbox_max_size: int
    # heartbeat
    heartbeat_interval_s: float
    # logging
    log_level: str

    def topic_events(self) -> str:
        return f"nodes/{self.node_id}/events"

    def topic_heartbeat(self) -> str:
        return f"nodes/{self.node_id}/heartbeat"

    def topic_status(self) -> str:
        return f"nodes/{self.node_id}/status"


def load_config(*, exit_on_error: bool = True) -> EdgeConfig:
    """Load and validate edge configuration."""
    missing: List[str] = []

    def required(name: str, cast: Callable = str):
        value = _get(name, cast=cast)
        if value is _MISSING:
            missing.append(name)
            return None
        return value

    candidate = dict(
        node_id=required("NODE_ID"),
        node_name=_get("NODE_NAME", "Unnamed Node"),
        camera_source=_get("CAMERA_SOURCE", "0"),
        target_fps=_get("TARGET_FPS", 12.0, float),
        camera_failure_threshold=_get("CAMERA_FAILURE_THRESHOLD", 10, int),
        camera_recovery_reads=_get("CAMERA_RECOVERY_READS", 15, int),
        camera_backoff_base_s=_get("CAMERA_BACKOFF_BASE_S", 1.0, float),
        camera_backoff_max_s=_get("CAMERA_BACKOFF_MAX_S", 30.0, float),
        model_path=required("MODEL_PATH"),
        model_labels_path=_get("MODEL_LABELS_PATH", ""),
        model_input_size=_get("MODEL_INPUT_SIZE", 320, int),
        confidence_threshold=_get("CONFIDENCE_THRESHOLD", 0.45, float),
        nms_iou_threshold=_get("NMS_IOU_THRESHOLD", 0.45, float),
        inference_max_recovery_attempts=_get("INFERENCE_MAX_RECOVERY_ATTEMPTS", 5, int),
        event_debounce_seconds=_get("EVENT_DEBOUNCE_SECONDS", 5.0, float),
        snapshot_enabled=_get("SNAPSHOT_ENABLED", True, _as_bool),
        snapshot_max_bytes=_get("SNAPSHOT_MAX_BYTES", 51200, int),
        snapshot_min_jpeg_quality=_get("SNAPSHOT_MIN_JPEG_QUALITY", 30, int),
        mqtt_host=required("MQTT_HOST"),
        mqtt_port=_get("MQTT_PORT", 8883, int),
        mqtt_username=required("MQTT_USERNAME"),
        mqtt_password=required("MQTT_PASSWORD"),
        mqtt_use_tls=_get("MQTT_USE_TLS", True, _as_bool),
        mqtt_ca_cert=_get("MQTT_CA_CERT", ""),
        mqtt_qos=_get("MQTT_QOS", 1, int),
        outbox_max_size=_get("OUTBOX_MAX_SIZE", 1000, int),
        heartbeat_interval_s=_get("HEARTBEAT_INTERVAL_S", 10.0, float),
        log_level=_get("LOG_LEVEL", "INFO"),
    )

    if missing:
        msg = "Missing required environment variable(s): " + ", ".join(sorted(missing))
        logger.error(msg)
        if exit_on_error:
            # Fail fast: never run partially configured.
            sys.stderr.write(msg + "\n")
            sys.exit(1)
        raise ConfigError(msg)

    return EdgeConfig(**candidate)  # type: ignore[arg-type]
