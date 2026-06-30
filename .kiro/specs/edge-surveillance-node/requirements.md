# Requirements Document

Edge-Surveillance-Node

## Introduction

Edge-Surveillance-Node is an end-to-end computer-vision surveillance platform built for resource-constrained edge hardware (Raspberry Pi / Jetson Nano). An edge agent captures frames with OpenCV, runs object detection through a quantized (INT8) ONNX model, and publishes lightweight detection events over MQTT to a central ingestion service. Operators monitor their fleet of devices and review detection events through a modern, professional web dashboard.

The system is designed around three hard constraints that drive every requirement:

1. **Constrained compute** — models must be quantized to INT8 to run at usable frame rates on weak hardware.
2. **Constrained bandwidth** — the edge node transmits event-driven metadata and compressed snapshots, never a 24/7 video stream.
3. **Constrained connectivity** — edge nodes operate over unreliable networks and must buffer, reconnect, and recover gracefully.

The deployment target is a split topology: the edge agent runs on-device, the ingestion + API + dashboard backend deploys to **Render**, and the web dashboard frontend deploys to **Vercel**.

## Glossary

- **Edge Node / Agent** — the on-device Python process performing capture, inference, and publishing.
- **Detection Event** — a structured message describing one or more detected objects at a point in time.
- **Heartbeat** — a periodic liveness message reporting node health and status (`healthy` / `degraded`).
- **Snapshot** — a single compressed JPEG frame attached to a detection event.
- **Broker** — the MQTT broker brokering messages between edge nodes and the ingestion service.
- **Ingestion Service** — the backend MQTT subscriber that validates, persists, and fans out events.
- **Dashboard** — the operator-facing web application.

---

## Requirements

### Requirement 1: Edge Frame Capture & Camera Lifecycle

**User Story:** As an operator, I want the edge node to reliably capture frames from a connected camera, so that detection runs on a continuous, healthy video source.

#### Acceptance Criteria

1. WHEN the agent starts THEN the system SHALL open the configured camera device via OpenCV and begin a capture loop at the configured target frame rate.
2. WHEN a frame is captured successfully THEN the system SHALL make the most recent frame available to the inference pipeline.
3. WHEN frame capture fails for a single frame THEN the system SHALL log a warning and continue the capture loop without crashing.
4. WHEN the camera becomes unavailable (device read failures exceed a configurable threshold) THEN the system SHALL enter `degraded` status and begin reconnection attempts using exponential backoff.
5. WHILE the camera is unavailable THE system SHALL emit `degraded` heartbeats, and the `degraded` status SHALL persist until explicitly cleared by a successful reconnection AND a configurable number of consecutive successful frame reads (the device is considered recovered only after demonstrated stable capture, not merely on reconnect).
6. WHEN reconnection succeeds AND stable capture is confirmed THEN the system SHALL clear the `degraded` status and resume `healthy` heartbeats.
7. IF the camera device reports as available but reads continue to fail for other reasons (corrupt frames, driver errors) THEN the system SHALL still trigger the reconnection/backoff path rather than spinning silently.

> Resolution (Q2): degraded status persists until explicitly cleared by confirmed stable recovery. (Q3): reconnection is triggered by sustained read failure regardless of whether the OS reports the device as present.

---

### Requirement 2: Model Quantization Toolchain

**User Story:** As an ML engineer, I want a reproducible tool to quantize a float32 model to INT8 ONNX, so that detection runs fast within edge hardware limits.

#### Acceptance Criteria

1. WHEN the quantization tool is invoked with a source model and a representative dataset THEN the system SHALL produce an INT8 quantized ONNX model artifact.
2. WHEN producing the quantized model THEN the system SHALL perform calibration using the representative dataset before quantization.
3. WHEN quantization completes THEN the system SHALL report the model size reduction ratio and the measured accuracy delta against the float32 baseline.
4. WHEN the measured accuracy delta is greater than OR equal to 5 percent THEN the system SHALL emit a warning (the boundary value of exactly 5% triggers the warning).
5. IF the representative dataset is missing OR corrupted THEN the system SHALL fail immediately with a clear, actionable error and SHALL NOT fall back to default/random calibration (silent low-quality calibration is unacceptable for a safety-relevant pipeline).
6. WHEN the tool finishes successfully THEN the system SHALL validate that the output model loads in ONNX Runtime before declaring success.

> Resolution (Q4): `>= 5%` triggers the warning. (Q5): fail fast on missing/corrupt calibration data.

---

### Requirement 3: Edge Inference Engine

**User Story:** As an operator, I want the edge node to run object detection locally, so that detections are produced without streaming video off-device.

#### Acceptance Criteria

1. WHEN the agent starts THEN the system SHALL load the quantized ONNX model into ONNX Runtime.
2. WHEN a frame is available THEN the system SHALL run inference and produce zero or more object detections with class labels and confidence scores.
3. WHEN inference completes THEN the system SHALL record inference latency and effective FPS metrics.
4. IF the model fails to load OR inference cannot proceed for any reason (corrupt model, incompatible input shape, runtime exception) THEN the system SHALL log the error, emit a `degraded` heartbeat, and halt the inference loop.
5. WHEN the inference loop has halted due to a model/inference failure THEN the system SHALL attempt automatic recovery with bounded exponential backoff up to a configurable maximum number of attempts; after the maximum is exhausted THE system SHALL remain in `degraded` state and require manual intervention rather than retrying forever.
6. WHILE inference is halted THE capture loop and heartbeat loop SHALL continue running so the node remains observable.

> Resolution (Q6): any inference failure (not only load failure) enters the degraded/halt path. (Q7): bounded auto-recovery, then require manual intervention.

---

### Requirement 4: Detection Event Generation & Snapshot Handling

**User Story:** As an operator, I want detection events with optional snapshots, so that I can review what triggered an alert without receiving continuous video.

#### Acceptance Criteria

1. WHEN one or more detections meet OR exceed the configurable minimum confidence threshold THEN the system SHALL create a detection event; detections below the threshold SHALL NOT generate events (suppress low-confidence false positives).
2. WHEN a detection event is created THEN it SHALL include node ID, timestamp (UTC, ISO-8601), detected object classes with confidence scores, and bounding boxes.
3. WHEN a detection event is created THEN the system SHALL optionally attach a compressed JPEG snapshot of the triggering frame, per configuration.
4. WHEN a snapshot is attached THEN the system SHALL compress it as JPEG to minimize bandwidth.
5. WHEN encoding a snapshot THEN the system SHALL respect a configurable maximum snapshot byte size.
6. IF a compressed JPEG exceeds the maximum size THEN the system SHALL progressively reduce JPEG quality (and downscale if needed) to fit under the limit rather than dropping the snapshot entirely; only if the minimum acceptable quality still exceeds the limit SHALL the event be sent without a snapshot, with a flag noting omission.

> Resolution (Q8): minimum confidence threshold required. (Q9): compress-to-fit, omit only as last resort with a flag.

---

### Requirement 5: MQTT Publishing, Buffering & Recovery

**User Story:** As an operator, I want events delivered reliably over MQTT even on flaky networks, so that I do not lose detections during outages.

#### Acceptance Criteria

1. WHEN the agent starts THEN the system SHALL connect to the MQTT broker using authenticated credentials and TLS.
2. WHEN a detection event or heartbeat is produced THEN the system SHALL publish it to the appropriate MQTT topic with an appropriate QoS for reliable delivery.
3. WHEN the broker connection is lost THEN the system SHALL buffer outgoing events in a bounded local queue (oldest dropped first when full, with a logged metric).
4. WHEN the connection is re-established AFTER a real disconnection AND the buffer is non-empty THEN the system SHALL republish queued events in order.
5. IF no disconnection occurred OR the queue is empty THEN the system SHALL NOT trigger any republish activity.
6. WHEN publishing THEN the system SHALL use a stable per-node client ID and a Last Will and Testament message marking the node offline on unexpected disconnect.

> Resolution (Q10): republish only after a genuine disconnect with a non-empty queue.

---

### Requirement 6: Ingestion Service & Fleet State

**User Story:** As an operator, I want a backend that ingests, validates, and tracks all node messages, so that the dashboard reflects accurate fleet state.

#### Acceptance Criteria

1. WHEN the ingestion service starts THEN it SHALL subscribe to detection and heartbeat topics on the broker.
2. WHEN a message is received THEN the system SHALL validate it against a schema and reject malformed messages with a logged error.
3. WHEN a valid detection event is received THEN the system SHALL persist it durably.
4. WHEN a valid heartbeat is received THEN the system SHALL update the node's last-seen timestamp and status.
5. WHEN snapshot data is received THEN the system SHALL store it in object storage and persist a reference, not the binary blob, in the primary record.
6. WHEN no heartbeat is received from a node within the configurable timeout THEN the system SHALL mark the node `offline`; a node SHALL NOT be marked offline at the exact instant it was last seen (offline requires `now - last_seen > timeout`, strictly greater).

> Resolution (Q11): strict inequality — never mark offline at the last-seen timestamp.

---

### Requirement 7: Real-Time API & WebSocket Push

**User Story:** As an operator, I want the dashboard to update in real time, so that I see detections as they happen.

#### Acceptance Criteria

1. WHEN the dashboard requests fleet status THEN the API SHALL return the current list of nodes with status and last-seen times.
2. WHEN the dashboard requests events THEN the API SHALL return paginated, filterable detection events.
3. WHEN the dashboard requests a snapshot THEN the API SHALL return a time-limited signed URL to the stored image.
4. WHEN a detection event is fully committed to durable storage THEN the system SHALL push it to subscribed dashboard clients over WebSocket within 2 seconds; the push SHALL occur only after the commit completes.
5. IF no actual detection event occurred THEN the system SHALL NOT emit any WebSocket push (no synthetic/empty pushes).
6. WHEN a WebSocket client connects THEN the connection SHALL be authenticated before any event data is delivered.

> Resolution (Q12): no pushes without a real event. (Q13): push only after the event is committed to storage.

---

### Requirement 8: Operator Dashboard (Frontend UX)

**User Story:** As an operator, I want a modern, professional dashboard, so that monitoring the fleet is clear and efficient.

#### Acceptance Criteria

1. WHEN an operator opens the dashboard THEN the system SHALL present a fleet overview (node count, online/offline/degraded counts, recent events).
2. WHEN an operator selects a node THEN the system SHALL show node detail: status history, health metrics (FPS, latency), and recent detections.
3. WHEN a new detection arrives over WebSocket THEN the UI SHALL update live without a full page reload.
4. WHEN an operator views an event THEN the system SHALL display its snapshot (if present), classes, confidences, and timestamp in operator-local time.
5. WHEN an operator filters events (by node, class, time range) THEN the system SHALL reflect the filtered results.
6. WHEN the viewport width is between 360 and 1920 pixels THEN the layout SHALL render correctly; below 360 pixels the layout SHALL still render as best it can (graceful degradation) rather than blocking rendering.
7. WHILE branded visual assets have not been supplied THE dashboard SHALL display neutral, professional placeholders (logo mark, hero) consistent with the design system.
8. WHEN branded assets are supplied THEN the dashboard SHALL use them; updated assets SHALL appear on next load (no forced live hot-swap requirement).

> Resolution (Q14): neutral professional placeholders. (Q15): assets apply on next load. (Q16): render as best it can below 360px.

---

### Requirement 9: Authentication, Authorization & Security

**User Story:** As a security-conscious operator, I want the platform secured end-to-end, so that only authorized parties access data and devices.

#### Acceptance Criteria

1. WHEN a user authenticates THEN the system SHALL issue a signed JWT and require it for all protected API and WebSocket access.
2. WHEN the broker receives a connection THEN it SHALL authenticate the client; WHEN authentication fails with invalid credentials THEN the broker SHALL reject the connection and SHALL NOT accept unauthenticated connections under any configuration.
3. WHEN any client/server communication occurs over the network THEN it SHALL use TLS.
4. WHEN role-based actions are attempted THEN the system SHALL enforce roles (e.g., `admin`, `viewer`) on protected endpoints.
5. WHEN secrets/credentials are needed THEN they SHALL be sourced from environment/configuration and SHALL NOT be committed to the repository.
6. WHEN an administrator configures JWT lifetime THEN the system SHALL cap it at 24 hours; an attempt to configure a longer lifetime SHALL be rejected with a clear validation error (not silently clamped).

> Resolution (Q1): broker rejects failed auth, never accepts unauthenticated. (Q17): reject over-limit JWT lifetime configuration.

---

### Requirement 10: Bandwidth Optimization

**User Story:** As an operator on metered/limited connectivity, I want minimal data usage, so that the system is affordable and resilient.

#### Acceptance Criteria

1. WHEN no qualifying detection occurs THEN the system SHALL transmit only periodic heartbeats, never video frames.
2. WHEN transmitting detection metadata THEN the system SHALL use a compact serialization format.
3. WHEN repeated identical detections persist THEN the system SHALL apply a configurable debounce/cooldown per object class to avoid event floods.
4. WHEN snapshots are sent THEN they SHALL be compressed and size-bounded per Requirement 4.

---

### Requirement 11: Observability & Metrics

**User Story:** As an operator, I want health and performance metrics, so that I can diagnose nodes and the backend.

#### Acceptance Criteria

1. WHEN the agent runs THEN it SHALL expose/emit health metrics (FPS, inference latency, dropped frames, queue depth, connection state).
2. WHEN the backend runs THEN it SHALL expose health and readiness endpoints suitable for Render health checks.
3. WHEN errors occur THEN components SHALL emit structured logs with severity and context.
4. WHEN inference latency and FPS are recorded THEN the system SHALL record metrics during active processing; during idle periods (no frames processed) the system SHALL skip metric samples rather than recording misleading zero values, while still reporting an explicit `idle` state.

> Resolution (Q18): skip metrics while idle, report idle state instead of zeros.

---

### Requirement 12: Configuration, Schema & Deployment Readiness

**User Story:** As an operator, I want predictable configuration and deployment, so that I can run this on Render and Vercel reliably.

#### Acceptance Criteria

1. WHEN any component starts THEN it SHALL load configuration from environment variables with documented defaults where safe.
2. WHEN the frontend builds THEN it SHALL be deployable to Vercel with environment-based API/WebSocket endpoints.
3. WHEN the backend deploys THEN it SHALL be deployable to Render with health checks and a managed database/object store.
4. WHEN the backend starts AND the database schema is absent THEN the system SHALL apply the schema automatically; WHEN the schema already exists THEN the system SHALL verify it via versioned migrations and apply any pending migrations rather than skipping verification entirely.
5. IF a required environment variable is missing THEN the component SHALL log the specific missing variable name(s) and terminate immediately (fail fast); it SHALL NOT attempt to run in a partially-configured degraded mode.

> Resolution (Q19): verify/migrate existing schema, don't blindly skip. (Q20): log the missing variable name then fail fast.
