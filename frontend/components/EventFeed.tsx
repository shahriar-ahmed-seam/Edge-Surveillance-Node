"use client";

import { AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";

import { fetchEvents } from "@/lib/api";
import { createLiveClient } from "@/lib/ws";
import type { EventInfo, LiveDetection } from "@/lib/types";
import { EventCard } from "./EventCard";
import { Filters, type FilterValue } from "./Filters";
import type { NodeInfo } from "@/lib/types";

interface Props {
  nodes: NodeInfo[];
  nodeId?: string;
  live?: boolean;
}

const MAX_EVENTS = 100;

export function EventFeed({ nodes, nodeId, live = true }: Props) {
  const [events, setEvents] = useState<EventInfo[]>([]);
  const [filter, setFilter] = useState<FilterValue>({
    node_id: nodeId ?? "",
    label: "",
    since: "",
  });
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("closed");
  const [loading, setLoading] = useState(true);
  const filterRef = useRef(filter);
  filterRef.current = filter;

  // Load (and reload on filter change) the historical page.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchEvents({
      node_id: filter.node_id || undefined,
      label: filter.label || undefined,
      since: filter.since ? new Date(filter.since).toISOString() : undefined,
      limit: MAX_EVENTS,
    })
      .then((page) => {
        if (!cancelled) setEvents(page.items);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filter.node_id, filter.label, filter.since]);

  // Live updates over WebSocket without full page reload.
  useEffect(() => {
    if (!live) return;
    const client = createLiveClient({
      onStatus: setStatus,
      onMessage: (msg: LiveDetection) => {
        const f = filterRef.current;
        if (f.node_id && msg.node_id !== f.node_id) return;
        if (f.label && !msg.detections.some((d) => d.label === f.label)) return;
        const incoming: EventInfo = {
          event_id: msg.event_id,
          node_id: msg.node_id,
          timestamp: msg.timestamp,
          snapshot_ref: msg.snapshot_ref,
          snapshot_omitted_reason: null,
          metrics: msg.metrics,
          detections: msg.detections,
        };
        setEvents((prev) => {
          if (prev.some((e) => e.event_id === incoming.event_id)) return prev;
          return [incoming, ...prev].slice(0, MAX_EVENTS);
        });
      },
    });
    return () => client.close();
  }, [live]);

  const headerLabel = useMemo(
    () => (status === "open" ? "Live" : status === "connecting" ? "Connecting" : "Offline"),
    [status]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-content">Detection Events</h2>
        {live && (
          <span className="inline-flex items-center gap-1.5 text-xs text-content-muted">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                status === "open" ? "bg-status-online animate-pulse-ring" : "bg-status-offline"
              }`}
            />
            {headerLabel}
          </span>
        )}
      </div>

      {!nodeId && <Filters nodes={nodes} value={filter} onChange={setFilter} />}

      {loading ? (
        <p className="text-sm text-content-faint">Loading events…</p>
      ) : events.length === 0 ? (
        <p className="rounded-lg border border-dashed border-surface-border p-8 text-center text-sm text-content-faint">
          No detection events match the current filters.
        </p>
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2">
          <AnimatePresence initial={false}>
            {events.map((e) => (
              <EventCard key={e.event_id} event={e} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
