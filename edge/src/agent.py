"""Edge agent: wires capture, inference, events, and MQTT publishing."""
from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timezone

from .camera import CameraSource
from .config import EdgeConfig, load_config
from .events import EventFactory
from .health import HealthState
from .inference import Detector, InferenceError, load_labels
from .mqtt_client import MqttPublisher
from .snapshot import SnapshotEncoder

logger = logging.getLogger("edge.agent")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class EdgeAgent:
    def __init__(self, config: EdgeConfig):
        self.config = config
        self.health = HealthState()
        self._stop = threading.Event()

        self.camera = CameraSource(
            config.camera_source,
            target_fps=config.target_fps,
            failure_threshold=config.camera_failure_threshold,
            recovery_reads=config.camera_recovery_reads,
            backoff_base_s=config.camera_backoff_base_s,
            backoff_max_s=config.camera_backoff_max_s,
        )
        self.detector = Detector(
            config.model_path,
            labels=load_labels(config.model_labels_path),
            input_size=config.model_input_size,
            confidence_threshold=config.confidence_threshold,
            iou_threshold=config.nms_iou_threshold,
            max_recovery_attempts=config.inference_max_recovery_attempts,
        )
        self.events = EventFactory(
            config.node_id,
            confidence_threshold=config.confidence_threshold,
            debounce_seconds=config.event_debounce_seconds,
        )
        self.snapshots = SnapshotEncoder(
            max_bytes=config.snapshot_max_bytes,
            min_quality=config.snapshot_min_jpeg_quality,
        )
        self.mqtt = MqttPublisher(
            host=config.mqtt_host,
            port=config.mqtt_port,
            username=config.mqtt_username,
            password=config.mqtt_password,
            node_id=config.node_id,
            use_tls=config.mqtt_use_tls,
            ca_cert=config.mqtt_ca_cert,
            qos=config.mqtt_qos,
            outbox_max_size=config.outbox_max_size,
            status_topic=config.topic_status(),
        )

    # -- loops ------------------------------------------------------------
    def _inference_loop(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            if self.detector.halted:
                if self.detector.exhausted:
                    # Stay degraded; require manual intervention.
                    self.health.inference_exhausted = True
                    self._stop.wait(5.0)
                    continue
                recovered = self.detector.attempt_recovery()
                self.health.inference_halted = not recovered
                if not recovered:
                    self._stop.wait(min(backoff, 30.0))
                    backoff *= 2
                    continue
                backoff = 1.0

            frame, _ = self.camera.latest_frame()
            if frame is None:
                self.health.idle = True
                self._stop.wait(0.1)
                continue

            try:
                detections = self.detector.infer(frame)
            except InferenceError as exc:
                logger.error("Inference halted: %s", exc)
                self.health.inference_halted = True
                continue

            self.health.inference_halted = False
            self.health.idle = False
            self.health.fps = self.detector.metrics.fps
            self.health.inference_ms = self.detector.metrics.inference_ms

            snapshot_meta = None
            if detections and self.config.snapshot_enabled:
                result = self.snapshots.encode(frame)
                snapshot_meta = {
                    "present": result.present,
                    "format": "jpeg" if result.present else None,
                    "bytes": len(result.data) if result.data else 0,
                    "omitted_reason": result.omitted_reason,
                    # base64 payload attached by transport layer if present
                    "data_b64": _b64(result.data) if result.data else None,
                }

            event = self.events.build(
                detections,
                metrics={
                    "inference_ms": self.detector.metrics.inference_ms,
                    "fps": self.detector.metrics.fps,
                },
                snapshot_meta=snapshot_meta,
            )
            if event is not None:
                # Event-driven transmission only.
                self.mqtt.publish(self.config.topic_events(), event)

    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            self.health.camera_degraded = self.camera.is_degraded
            self.health.queue_depth = self.mqtt.queue_depth
            self.health.dropped_frames = self.mqtt.dropped_count
            self.health.connection = "connected" if self.mqtt.connected else "disconnected"
            hb = self.health.heartbeat(self.config.node_id, _utc_now())
            self.mqtt.publish(self.config.topic_heartbeat(), hb)
            self._stop.wait(self.config.heartbeat_interval_s)

    # -- lifecycle --------------------------------------------------------
    def start(self) -> None:
        logger.info("Starting edge agent %s", self.config.node_id)
        try:
            self.detector.load()
        except InferenceError as exc:
            # Halt inference but keep the node observable.
            logger.error("Initial model load failed: %s", exc)
            self.health.inference_halted = True

        self.camera.start()
        try:
            self.mqtt.connect()
        except Exception as exc:
            logger.error("Initial MQTT connect failed (will buffer): %s", exc)

        threads = [
            threading.Thread(target=self._inference_loop, name="inference", daemon=True),
            threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True),
        ]
        for t in threads:
            t.start()
        self._threads = threads

    def stop(self) -> None:
        logger.info("Stopping edge agent")
        self._stop.set()
        self.camera.stop()
        self.mqtt.disconnect()

    def run_forever(self) -> None:
        self.start()
        try:
            while not self._stop.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


def main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    agent = EdgeAgent(config)

    def _handle(signum, frame):
        agent.stop()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    agent.run_forever()


if __name__ == "__main__":
    main()
