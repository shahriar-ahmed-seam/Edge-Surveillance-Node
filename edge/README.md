# Edge Agent

On-device agent for Raspberry Pi / Jetson Nano. Captures frames with OpenCV,
runs quantized INT8 ONNX inference, and publishes detection events + heartbeats
over MQTT with local buffering for resilience.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env          # then edit values
python -m src.agent
```

## Run with Docker

```bash
docker build -t edge-surveillance-node-agent .
docker run --rm \
  --env-file .env \
  --device /dev/video0 \
  -v $(pwd)/models:/app/models \
  edge-surveillance-node-agent
```

## Architecture

Three cooperating threads coordinate through thread-safe shared state:

- **Capture loop** (`camera.py`) — reads frames, tracks health, reconnects with backoff.
- **Inference loop** (`inference.py` + `agent.py`) — runs detection, builds events, publishes.
- **Heartbeat loop** (`health.py`) — periodic liveness + metrics.

If inference halts, capture and heartbeat keep running so the node stays
observable. See [`../.kiro/specs/edge-surveillance-node/design.md`](../.kiro/specs/edge-surveillance-node/design.md).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
