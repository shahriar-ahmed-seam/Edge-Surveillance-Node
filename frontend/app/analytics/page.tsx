"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { HorizontalBars } from "@/components/charts/HorizontalBars";
import { LineChart } from "@/components/charts/LineChart";
import { fetchAnalytics, downloadExport } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

const RANGES = [
  { days: 7, label: "7D" },
  { days: 14, label: "14D" },
  { days: 30, label: "30D" },
];

function shortDay(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function AnalyticsView() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchAnalytics(days)
      .then((d) => active && setData(d))
      .catch(() => active && setData(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [days]);

  const labels = data?.time_series.map((p) => shortDay(p.date)) ?? [];

  const exportData = async (fmt: "csv" | "json") => {
    try {
      await downloadExport(fmt, days);
    } catch {
      /* surfaced via disabled state in a fuller build */
    }
  };

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-content">Analytics</h1>
          <p className="mt-1 text-sm text-content-muted">
            Fleet-wide detection trends, class distribution, and performance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 rounded-full border border-surface-border bg-surface-overlay p-1">
            <button
              onClick={() => exportData("csv")}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-content-muted transition-colors hover:text-content"
            >
              Export CSV
            </button>
            <button
              onClick={() => exportData("json")}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-content-muted transition-colors hover:text-content"
            >
              JSON
            </button>
          </div>
          <div className="flex items-center gap-1 rounded-full border border-surface-border bg-surface-raised p-1">
            {RANGES.map((r) => (
              <button
                key={r.days}
                onClick={() => setDays(r.days)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                  days === r.days
                    ? "bg-accent text-surface"
                    : "text-content-muted hover:text-content"
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && !data ? (
        <p className="text-sm text-content-faint">Loading analytics…</p>
      ) : !data ? (
        <p className="card p-8 text-center text-sm text-content-faint">No analytics available.</p>
      ) : (
        <div className="space-y-5">
          {/* KPI tiles */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="Total Events" value={data.totals.events.toLocaleString()} />
            <Kpi label="Detections" value={data.totals.detections.toLocaleString()} />
            <Kpi label="Avg Confidence" value={`${(data.totals.avg_confidence * 100).toFixed(0)}%`} bright />
            <Kpi label="Active Nodes" value={String(data.totals.active_nodes)} />
          </div>

          {/* Detection volume over time */}
          <div className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-content">Detection Volume</h2>
              <span className="flex items-center gap-1.5 text-xs text-content-muted">
                <span className="h-2 w-2 rounded-full bg-accent" /> Events / day
              </span>
            </div>
            <LineChart
              labels={labels}
              series={[{ values: data.time_series.map((p) => p.events), color: "#3BE66B", fill: true }]}
            />
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {/* Class distribution */}
            <div className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-content">Detections by Class</h2>
              <HorizontalBars
                items={data.by_class.map((c) => ({ label: c.label, value: c.count }))}
              />
            </div>
            {/* Per-node breakdown */}
            <div className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-content">Events by Node</h2>
              <HorizontalBars
                items={data.by_node.map((n) => ({
                  label: n.name,
                  sublabel: n.node_id,
                  value: n.count,
                }))}
              />
            </div>
          </div>

          {/* Performance: latency + fps */}
          <div className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-content">Performance Trend</h2>
              <div className="flex items-center gap-4 text-xs text-content-muted">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: "#3BE66B" }} /> Avg FPS
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: "#FBBF24" }} /> Inference (ms)
                </span>
              </div>
            </div>
            <LineChart
              labels={labels}
              series={[
                { values: data.latency_series.map((p) => p.avg_fps), color: "#3BE66B", fill: true },
                { values: data.latency_series.map((p) => p.avg_inference_ms), color: "#FBBF24" },
              ]}
            />
            <div className="mt-3 flex gap-6 text-xs text-content-muted">
              <span>
                Avg FPS: <span className="font-mono text-content">{data.totals.avg_fps}</span>
              </span>
              <span>
                Avg latency:{" "}
                <span className="font-mono text-content">{data.totals.avg_inference_ms} ms</span>
              </span>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function Kpi({ label, value, bright }: { label: string; value: string; bright?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        bright
          ? "border-accent/30 bg-tile-bright text-surface"
          : "border-surface-border bg-tile-green text-content"
      )}
    >
      <div className={cn("text-xs uppercase tracking-wide", bright ? "text-surface/70" : "text-content-muted")}>
        {label}
      </div>
      <div className="mt-1.5 font-mono text-3xl font-semibold">{value}</div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <AuthGuard>
      <AnalyticsView />
    </AuthGuard>
  );
}
