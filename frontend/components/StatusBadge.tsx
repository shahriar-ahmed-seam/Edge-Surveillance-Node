import { cn } from "@/lib/utils";
import type { NodeStatus } from "@/lib/types";

const STYLES: Record<NodeStatus, { dot: string; text: string; label: string }> = {
  healthy: { dot: "bg-status-online", text: "text-status-online", label: "Online" },
  degraded: { dot: "bg-status-degraded", text: "text-status-degraded", label: "Degraded" },
  offline: { dot: "bg-status-offline", text: "text-status-offline", label: "Offline" },
};

export function StatusBadge({ status }: { status: NodeStatus }) {
  const s = STYLES[status] ?? STYLES.offline;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-surface-border bg-surface-overlay px-2.5 py-1 text-xs font-medium",
        s.text
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          s.dot,
          status === "healthy" && "animate-pulse-ring"
        )}
      />
      {s.label}
    </span>
  );
}
