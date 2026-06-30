"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchEvents } from "@/lib/api";
import { createLiveClient } from "@/lib/ws";
import type { EventInfo, LiveDetection } from "@/lib/types";
import { timeAgo } from "@/lib/utils";

const LABEL_ICON: Record<string, string> = {
  person: "🚶",
  car: "🚗",
  bicycle: "🚲",
  dog: "🐕",
  package: "📦",
};

export function RecentEvents({ limit = 8 }: { limit?: number }) {
  const [events, setEvents] = useState<EventInfo[]>([]);

  useEffect(() => {
    let active = true;
    fetchEvents({ limit }).then((p) => active && setEvents(p.items)).catch(() => {});
    const client = createLiveClient({
      onMessage: (msg: LiveDetection) => {
        const incoming: EventInfo = {
          event_id: msg.event_id,
          node_id: msg.node_id,
          timestamp: msg.timestamp,
          snapshot_ref: msg.snapshot_ref,
          snapshot_omitted_reason: null,
          metrics: msg.metrics,
          detections: msg.detections,
        };
        setEvents((prev) =>
          prev.some((e) => e.event_id === incoming.event_id)
            ? prev
            : [incoming, ...prev].slice(0, limit)
        );
      },
    });
    return () => {
      active = false;
      client.close();
    };
  }, [limit]);

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-content">Recent Detections</h2>
        <Link href="/events" className="text-xs text-accent hover:underline">
          View all
        </Link>
      </div>
      {events.length === 0 ? (
        <p className="py-6 text-center text-sm text-content-faint">No detections yet.</p>
      ) : (
        <ul className="space-y-1">
          <AnimatePresence initial={false}>
            {events.map((e) => {
              const top = [...e.detections].sort((a, b) => b.confidence - a.confidence)[0];
              const icon = LABEL_ICON[top?.label] ?? "🎯";
              return (
                <motion.li
                  key={e.event_id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-surface-overlay"
                >
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-surface-overlay text-base">
                    {icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-content">
                      {top?.label ?? "detection"}
                      {e.detections.length > 1 && (
                        <span className="text-content-faint"> +{e.detections.length - 1}</span>
                      )}
                    </div>
                    <div className="truncate font-mono text-[11px] text-content-faint">
                      {e.node_id} · {timeAgo(e.timestamp)}
                    </div>
                  </div>
                  <div className="shrink-0 font-mono text-sm text-accent">
                    {top ? `${(top.confidence * 100).toFixed(0)}%` : "—"}
                  </div>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}
