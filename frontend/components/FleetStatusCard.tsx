"use client";

import { DonutChart } from "@/components/charts/DonutChart";
import type { NodeInfo } from "@/lib/types";

export function FleetStatusCard({ nodes }: { nodes: NodeInfo[] }) {
  const online = nodes.filter((n) => n.status === "healthy").length;
  const degraded = nodes.filter((n) => n.status === "degraded").length;
  const offline = nodes.filter((n) => n.status === "offline").length;

  const slices = [
    { label: "Online", value: online, color: "#3BE66B" },
    { label: "Degraded", value: degraded, color: "#FBBF24" },
    { label: "Offline", value: offline, color: "#6B7B6B" },
  ];

  return (
    <div className="card p-5">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-content">Fleet Status</h2>
        <span className="rounded-full border border-surface-border px-2.5 py-1 text-[11px] text-content-muted">
          Live
        </span>
      </div>
      <div className="flex flex-col items-center">
        <DonutChart
          slices={slices}
          centerLabel="Total Nodes"
          centerValue={String(nodes.length)}
          size={190}
        />
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {slices.map((s) => (
            <span
              key={s.label}
              className="inline-flex items-center gap-1.5 rounded-full bg-surface-overlay px-2.5 py-1 text-xs text-content-muted"
            >
              <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
              {s.label} {s.value}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
