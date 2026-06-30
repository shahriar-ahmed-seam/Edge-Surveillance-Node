"""MQTT ingestion worker."""
from __future__ import annotations

import base64
import logging
import ssl
from datetime import datetime, timezone

from ..db.models import Detection, Event, Node
from ..db.session import session_scope
from ..services.event_bus import EventBus
from ..storage.object_store import ObjectStore
from .validators import EventIn, HeartbeatIn, ValidationError

logger = logging.getLogger("backend.ingestion")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionWorker:
    def __init__(self, settings, object_store: ObjectStore, event_bus: EventBus,
                 client_factory=None):
        self._settings = settings
        self._store = object_store
        self._bus = event_bus
        self._client_factory = client_factory or self._paho_client
        self._client = None

    # -- paho wiring ------------------------------------------------------
    def _paho_client(self):
        import paho.mqtt.client as mqtt

        client = mqtt.Client(client_id="ingestion-worker", clean_session=False)
        client.username_pw_set(self._settings.mqtt_username, self._settings.mqtt_password)
        if self._settings.mqtt_use_tls:
            if self._settings.mqtt_ca_cert:
                client.tls_set(ca_certs=self._settings.mqtt_ca_cert,
                               tls_version=ssl.PROTOCOL_TLS_CLIENT)
            else:
                client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        return client

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc != 0:
            logger.error("Ingestion MQTT connect failed rc=%s", rc)
            return
        client.subscribe(self._settings.mqtt_topic_events, qos=1)
        client.subscribe(self._settings.mqtt_topic_heartbeat, qos=1)
        logger.info("Ingestion subscribed to events and heartbeat topics")

    def _on_message(self, client, userdata, msg):
        try:
            self.handle_message(msg.topic, msg.payload)
        except Exception as exc:  # never let the callback die
            logger.exception("Error handling message on %s: %s", msg.topic, exc)

    # -- message handling (testable) -------------------------------------
    def handle_message(self, topic: str, payload: bytes) -> None:
        if topic.endswith("/heartbeat"):
            self._handle_heartbeat(payload)
        elif topic.endswith("/events"):
            self._handle_event(payload)
        else:
            logger.debug("Ignoring message on unrecognized topic %s", topic)

    def _handle_heartbeat(self, payload: bytes) -> None:
        try:
            hb = HeartbeatIn.model_validate_json(payload)
        except ValidationError as exc:
            logger.error("Rejected malformed heartbeat: %s", exc)
            return
        with session_scope() as db:
            node = db.get(Node, hb.node_id)
            now = _utcnow()
            if node is None:
                node = Node(node_id=hb.node_id, name=hb.node_id, first_seen=now)
                db.add(node)
            node.status = hb.status
            node.last_seen = now
            node.last_metrics = hb.metrics

    def _handle_event(self, payload: bytes) -> None:
        try:
            evt = EventIn.model_validate_json(payload)
        except ValidationError as exc:
            logger.error("Rejected malformed event: %s", exc)
            return

        snapshot_ref = None
        omitted_reason = None
        if evt.snapshot is not None:
            omitted_reason = evt.snapshot.omitted_reason
            if evt.snapshot.present and evt.snapshot.data_b64:
                try:
                    raw = base64.b64decode(evt.snapshot.data_b64)
                    snapshot_ref = self._store.put_snapshot(raw)
                except Exception as exc:
                    logger.warning("Failed to store snapshot: %s", exc)
                    omitted_reason = omitted_reason or "storage_error"

        with session_scope() as db:
            # ensure node row exists
            if db.get(Node, evt.node_id) is None:
                db.add(Node(node_id=evt.node_id, name=evt.node_id, first_seen=_utcnow()))
            if db.get(Event, evt.event_id) is not None:
                logger.debug("Duplicate event %s ignored", evt.event_id)
                return
            event = Event(
                event_id=evt.event_id,
                node_id=evt.node_id,
                timestamp=evt.timestamp,
                created_at=_utcnow(),
                snapshot_ref=snapshot_ref,
                snapshot_omitted_reason=omitted_reason,
                metrics=evt.metrics,
            )
            for d in evt.detections:
                event.detections.append(
                    Detection(label=d.label, confidence=d.confidence, bbox=d.bbox)
                )
            db.add(event)
        # session_scope commits here. Publish to WS only AFTER commit.
        self._bus.publish_threadsafe(
            {
                "type": "detection",
                "event_id": evt.event_id,
                "node_id": evt.node_id,
                "timestamp": evt.timestamp.isoformat(),
                "detections": [d.model_dump() for d in evt.detections],
                "snapshot_ref": snapshot_ref,
                "metrics": evt.metrics,
            }
        )

    # -- lifecycle --------------------------------------------------------
    def start(self) -> None:
        self._client = self._client_factory()
        # Non-blocking connect with background reconnection so startup never
        # hangs if the broker is not yet reachable.
        try:
            self._client.connect_async(self._settings.mqtt_host, self._settings.mqtt_port)
        except Exception as exc:
            logger.error("Ingestion connect_async failed: %s", exc)
        self._client.loop_start()
        logger.info("Ingestion worker started (async connect)")

    def stop(self) -> None:
        if self._client:
            try:
                self._client.loop_stop()
            except Exception:  # pragma: no cover
                pass
            self._client.disconnect()
