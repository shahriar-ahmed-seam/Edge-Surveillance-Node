import Link from "next/link";

import type { NodeInfo } from "@/lib/types";
import { timeAgo } from "@/lib/utils";
import { StatusBadge } from "./StatusBadge";

function metric(node: NodeInfo, key: string): string {
  const v = node.last_metrics?.[key];
  return v === undefined || v === null ? "—" : String(v);
}

export function NodeCard({ node }: { node: NodeInfo }) {
  return (
    <Link
      href={`/nodes/${encodeURIComponent(node.node_id)}`}
      className="card group block p-4 transition-colors hover:border-accent/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-medium text-content">{node.name}</h3>
          <p className="truncate font-mono text-xs text-content-faint">{node.node_id}</p>
        </div>
        <StatusBadge status={node.status} />
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
        <Stat label="FPS" value={metric(node, "fps")} />
        <Stat label="Latency" value={metric(node, "inference_ms")} unit="ms" />
        <Stat label="Queue" value={metric(node, "queue_depth")} />
      </dl>
      <p className="mt-3 text-xs text-content-faint">Last seen {timeAgo(node.last_seen)}</p>
    </Link>
  );
}

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-md bg-surface-overlay py-2">
      <div className="font-mono text-sm text-content">
        {value}
        {unit && value !== "—" ? <span className="text-content-faint"> {unit}</span> : null}
      </div>
      <div className="text-[10px] uppercase tracking-wide text-content-faint">{label}</div>
    </div>
  );
}
