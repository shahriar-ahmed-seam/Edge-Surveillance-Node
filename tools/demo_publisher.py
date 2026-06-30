"""Simulate an edge node for local testing.

Publishes heartbeats and detection events to the MQTT broker as if a real edge
agent were running, so the backend + dashboard can be exercised without a
camera or model. Not part of the production system.

Usage:
    python demo_publisher.py --node-id node-demo-01 --events 8
"""
from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

LABELS = ["person", "car", "bicycle", "dog", "package"]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def heartbeat(node_id: str, status: str = "healthy") -> dict:
    return {
        "schema_version": 1,
        "node_id": node_id,
        "timestamp": _utc(),
        "status": status,
        "metrics": {
            "fps": round(random.uniform(10, 14), 1),
            "inference_ms": round(random.uniform(30, 55), 1),
            "dropped_frames": random.randint(0, 3),
            "queue_depth": 0,
            "connection": "connected",
            "state": "active",
        },
    }


def detection_event(node_id: str) -> dict:
    n = random.randint(1, 3)
    dets = []
    for _ in range(n):
        dets.append(
            {
                "label": random.choice(LABELS),
                "confidence": round(random.uniform(0.55, 0.98), 3),
                "bbox": [
                    round(random.uniform(0, 200), 1),
                    round(random.uniform(0, 200), 1),
                    round(random.uniform(40, 120), 1),
                    round(random.uniform(40, 120), 1),
                ],
            }
        )
    return {
        "schema_version": 1,
        "node_id": node_id,
        "event_id": str(uuid.uuid4()),
        "timestamp": _utc(),
        "detections": dets,
        "metrics": {"fps": round(random.uniform(10, 14), 1),
                    "inference_ms": round(random.uniform(30, 55), 1)},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--username", default="edge")
    p.add_argument("--password", default="edge-secret")
    p.add_argument("--node-id", default="node-demo-01")
    p.add_argument("--name", default="Demo Camera (Front Door)")
    p.add_argument("--events", type=int, default=8, help="number of detection events")
    p.add_argument("--interval", type=float, default=2.0, help="seconds between events")
    args = p.parse_args()

    client = mqtt.Client(client_id=f"demo-{args.node_id}")
    client.username_pw_set(args.username, args.password)
    client.connect(args.host, args.port)
    client.loop_start()
    time.sleep(0.5)

    hb_topic = f"nodes/{args.node_id}/heartbeat"
    ev_topic = f"nodes/{args.node_id}/events"

    print(f"Publishing as {args.node_id} -> {args.host}:{args.port}")
    client.publish(hb_topic, json.dumps(heartbeat(args.node_id)), qos=1)
    print("  heartbeat sent")

    for i in range(args.events):
        evt = detection_event(args.node_id)
        client.publish(ev_topic, json.dumps(evt), qos=1)
        labels = ", ".join(d["label"] for d in evt["detections"])
        print(f"  event {i + 1}/{args.events}: {labels}")
        client.publish(hb_topic, json.dumps(heartbeat(args.node_id)), qos=1)
        time.sleep(args.interval)

    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
