export type NodeStatus = "healthy" | "degraded" | "offline";

export interface NodeInfo {
  node_id: string;
  name: string;
  status: NodeStatus;
  first_seen: string;
  last_seen: string;
  last_metrics: Record<string, unknown>;
}

export interface DetectionInfo {
  label: string;
  confidence: number;
  bbox: number[];
}

export interface EventInfo {
  event_id: string;
  node_id: string;
  timestamp: string;
  snapshot_ref: string | null;
  snapshot_omitted_reason: string | null;
  metrics: Record<string, unknown>;
  detections: DetectionInfo[];
}

export interface EventPage {
  items: EventInfo[];
  total: number;
  limit: number;
  offset: number;
}

export interface LiveDetection {
  type: "detection";
  event_id: string;
  node_id: string;
  timestamp: string;
  detections: DetectionInfo[];
  snapshot_ref: string | null;
  metrics: Record<string, unknown>;
}

export interface AnalyticsTotals {
  events: number;
  detections: number;
  active_nodes: number;
  avg_confidence: number;
  avg_inference_ms: number;
  avg_fps: number;
}

export interface TimePoint {
  date: string;
  events: number;
}

export interface LatencyPoint {
  date: string;
  avg_inference_ms: number;
  avg_fps: number;
}

export interface ClassCount {
  label: string;
  count: number;
}

export interface NodeCount {
  node_id: string;
  name: string;
  count: number;
}

export interface AnalyticsSummary {
  range_days: number;
  generated_at: string;
  totals: AnalyticsTotals;
  time_series: TimePoint[];
  latency_series: LatencyPoint[];
  by_class: ClassCount[];
  by_node: NodeCount[];
}
