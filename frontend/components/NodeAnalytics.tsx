"use client";

import { useEffect, useState } from "react";

import { downloadExport, fetchAnalytics } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";
import { HorizontalBars } from "./charts/HorizontalBars";
import { LineChart } from "./charts/LineChart";

function shortDay(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function NodeAnalytics({ nodeId }: { nodeId: string }) {
  const [data, setData] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    let active = true;
    fetchAnalytics(7, nodeId)
      .then((d) => active && setData(d))
      .catch(() => active && setData(null));
    return () => {
      active = false;
    };
  }, [nodeId]);

  if (!data) return null;

  const labels = data.time_series.map((p) => shortDay(p.date));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-content">Node Analytics · 7 days</h2>
        <button
          onClick={() => downloadExport("csv", 7, nodeId)}
          className="rounded-full border border-surface-border px-3 py-1.5 text-xs text-content-muted transition-colors hover:text-content"
        >
          Export CSV
        </button>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-content">Detection Volume</h3>
            <span className="flex items-center gap-1.5 text-xs text-content-muted">
              <span className="h-2 w-2 rounded-full bg-accent" /> Events / day
            </span>
          </div>
          <LineChart
            labels={labels}
            series={[
              { values: data.time_series.map((p) => p.events), color: "#3BE66B", fill: true },
            ]}
            height={200}
          />
        </div>
        <div className="card p-5">
          <h3 className="mb-4 text-sm font-semibold text-content">Top Classes</h3>
          <HorizontalBars items={data.by_class.map((c) => ({ label: c.label, value: c.count }))} />
        </div>
      </div>
    </div>
  );
}
