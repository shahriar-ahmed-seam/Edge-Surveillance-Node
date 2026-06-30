"""MQTT publisher with TLS auth, bounded outbox, and reconnect republish."""
from __future__ import annotations

import collections
import json
import logging
import ssl
import threading
from typing import Deque, Optional

logger = logging.getLogger("edge.mqtt")


class MqttPublisher:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        node_id: str,
        use_tls: bool = True,
        ca_cert: str = "",
        qos: int = 1,
        outbox_max_size: int = 1000,
        status_topic: Optional[str] = None,
        client_factory=None,
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._node_id = node_id
        self._use_tls = use_tls
        self._ca_cert = ca_cert
        self._qos = qos
        self._status_topic = status_topic or f"nodes/{node_id}/status"
        self._client_factory = client_factory or self._paho_client

        self._outbox: Deque[tuple] = collections.deque(maxlen=outbox_max_size)
        self._dropped_count = 0
        self._connected = False
        self._had_disconnect = False
        self._lock = threading.Lock()
        self._client = None

    # -- metrics ----------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def queue_depth(self) -> int:
        return len(self._outbox)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    # -- paho wiring ------------------------------------------------------
    def _paho_client(self):
        import paho.mqtt.client as mqtt

        # Stable per-node client ID.
        client = mqtt.Client(client_id=f"edge-{self._node_id}", clean_session=False)
        client.username_pw_set(self._username, self._password)
        if self._use_tls:
            if self._ca_cert:
                client.tls_set(ca_certs=self._ca_cert, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            else:
                client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        # Last Will and Testament marks node offline on unexpected drop.
        client.will_set(
            self._status_topic,
            payload=json.dumps({"node_id": self._node_id, "status": "offline"}),
            qos=1,
            retain=True,
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        return client

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            logger.info("MQTT connected to %s:%s", self._host, self._port)
            self._connected = True
            # Republish only after a real disconnect with queued items.
            if self._had_disconnect and self._outbox:
                self._flush_outbox()
            self._had_disconnect = False
        else:
            logger.error("MQTT connection refused rc=%s", rc)
            self._connected = False

    def _on_disconnect(self, client, userdata, rc, *args):
        logger.warning("MQTT disconnected rc=%s", rc)
        self._connected = False
        self._had_disconnect = True

    # -- lifecycle --------------------------------------------------------
    def connect(self) -> None:
        self._client = self._client_factory()
        self._client.connect(self._host, self._port)
        self._client.loop_start()

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        self._connected = False

    # -- publishing -------------------------------------------------------
    def _do_publish(self, topic: str, payload: str) -> bool:
        if self._client is None:
            return False
        try:
            info = self._client.publish(topic, payload, qos=self._qos)
            rc = getattr(info, "rc", 0)
            return rc == 0
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Publish raised: %s", exc)
            return False

    def _enqueue(self, topic: str, payload: str) -> None:
        with self._lock:
            if len(self._outbox) == self._outbox.maxlen:
                # Drop oldest first and account for it.
                self._dropped_count += 1
                logger.warning("Outbox full; dropping oldest (total dropped=%d)", self._dropped_count)
            self._outbox.append((topic, payload))

    def _flush_outbox(self) -> None:
        with self._lock:
            pending = list(self._outbox)
            self._outbox.clear()
        logger.info("Republishing %d queued message(s) after reconnect", len(pending))
        for topic, payload in pending:  # preserve FIFO order
            if not self._do_publish(topic, payload):
                self._enqueue(topic, payload)

    def publish(self, topic: str, message: dict) -> bool:
        """Publish a message, buffering to the outbox when disconnected."""
        payload = json.dumps(message, separators=(",", ":"))  # compact
        if self._connected and self._do_publish(topic, payload):
            return True
        self._enqueue(topic, payload)
        return False
