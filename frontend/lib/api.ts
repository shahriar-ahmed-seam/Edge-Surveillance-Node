import { getToken } from "./auth";
import type { AnalyticsSummary, EventPage, NodeInfo } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string; role: string }>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
}

export async function fetchNodes() {
  return request<NodeInfo[]>("/api/nodes");
}

export async function fetchNode(id: string) {
  return request<NodeInfo>(`/api/nodes/${encodeURIComponent(id)}`);
}

export interface EventQuery {
  node_id?: string;
  label?: string;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
}

export async function fetchEvents(q: EventQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(q).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== null) params.set(k, String(v));
  });
  const qs = params.toString();
  return request<EventPage>(`/api/events${qs ? `?${qs}` : ""}`);
}

export async function fetchSnapshotUrl(eventId: string) {
  return request<{ url: string }>(`/api/events/${encodeURIComponent(eventId)}/snapshot`);
}

export async function fetchAnalytics(days = 7, nodeId?: string) {
  const params = new URLSearchParams({ days: String(days) });
  if (nodeId) params.set("node_id", nodeId);
  return request<AnalyticsSummary>(`/api/analytics/summary?${params.toString()}`);
}

export async function downloadExport(fmt: "csv" | "json", days = 7, nodeId?: string) {
  const token = getToken();
  const params = new URLSearchParams({ fmt, days: String(days) });
  if (nodeId) params.set("node_id", nodeId);
  const res = await fetch(`${API_BASE}/api/analytics/export?${params.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Export failed");

  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `detections.${fmt}`;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export { ApiError, API_BASE };
