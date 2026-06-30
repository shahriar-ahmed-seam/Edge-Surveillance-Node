import type { NodeInfo } from "@/lib/types";

interface Props {
  nodes: NodeInfo[];
  eventCount: number;
}

export function FleetSummary({ nodes, eventCount }: Props) {
  const online = nodes.filter((n) => n.status === "healthy").length;
  const degraded = nodes.filter((n) => n.status === "degraded").length;
  const offline = nodes.filter((n) => n.status === "offline").length;

  const stats = [
    { label: "Total Nodes", value: nodes.length, accent: "text-content" },
    { label: "Online", value: online, accent: "text-status-online" },
    { label: "Degraded", value: degraded, accent: "text-status-degraded" },
    { label: "Offline", value: offline, accent: "text-status-offline" },
    { label: "Recent Events", value: eventCount, accent: "text-accent" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((s) => (
        <div key={s.label} className="card p-4">
          <div className="text-xs uppercase tracking-wide text-content-faint">{s.label}</div>
          <div className={`mt-1.5 font-mono text-2xl ${s.accent}`}>{s.value}</div>
        </div>
      ))}
    </div>
  );
}
