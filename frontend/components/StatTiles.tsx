import { cn } from "@/lib/utils";
import type { NodeInfo } from "@/lib/types";

interface Props {
  nodes: NodeInfo[];
  eventCount: number;
}

/** Summary stat tiles for fleet totals, online, degraded, and event counts. */
export function StatTiles({ nodes, eventCount }: Props) {
  const online = nodes.filter((n) => n.status === "healthy").length;
  const degraded = nodes.filter((n) => n.status === "degraded").length;

  const tiles = [
    { label: "Total Nodes", value: String(nodes.length), icon: "🛰️", bright: false },
    { label: "Online", value: String(online), icon: "🟢", bright: true },
    { label: "Degraded", value: String(degraded), icon: "⚠️", bright: false },
    { label: "Events Today", value: String(eventCount), icon: "🎯", bright: false },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {tiles.map((t) => (
        <div
          key={t.label}
          className={cn(
            "relative overflow-hidden rounded-xl border p-5",
            t.bright
              ? "border-accent/30 bg-tile-bright text-surface"
              : "border-surface-border bg-tile-green text-content"
          )}
        >
          <div className="mb-6 text-2xl">{t.icon}</div>
          <div
            className={cn(
              "text-xs uppercase tracking-wide",
              t.bright ? "text-surface/70" : "text-content-muted"
            )}
          >
            {t.label}
          </div>
          <div className="mt-1 font-mono text-3xl font-semibold">{t.value}</div>
        </div>
      ))}
    </div>
  );
}
