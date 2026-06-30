"use client";

import { motion } from "framer-motion";

import type { DetectionInfo, EventInfo } from "@/lib/types";
import { API_BASE } from "@/lib/api";
import { localTime } from "@/lib/utils";

function confidenceColor(c: number): string {
  if (c >= 0.8) return "text-status-online";
  if (c >= 0.6) return "text-status-degraded";
  return "text-content-muted";
}

export function EventCard({ event }: { event: EventInfo }) {
  const snapshotUrl = event.snapshot_ref
    ? `${API_BASE}/api/events/snapshot-file/${event.snapshot_ref}`
    : null;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      className="card overflow-hidden"
    >
      <div className="flex gap-3 p-3">
        <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-surface-overlay">
          {snapshotUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={snapshotUrl} alt="snapshot" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[10px] text-content-faint">
              {event.snapshot_omitted_reason ? "no img" : "—"}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-mono text-xs text-content-muted">{event.node_id}</span>
            <time className="shrink-0 text-xs text-content-faint">{localTime(event.timestamp)}</time>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {event.detections.map((d: DetectionInfo, i: number) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 rounded-md bg-surface-overlay px-2 py-0.5 text-xs"
              >
                <span className="text-content">{d.label}</span>
                <span className={`font-mono ${confidenceColor(d.confidence)}`}>
                  {(d.confidence * 100).toFixed(0)}%
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.article>
  );
}
