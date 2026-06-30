"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { FleetStatusCard } from "@/components/FleetStatusCard";
import { GreetingHeader } from "@/components/GreetingHeader";
import { NodeCard } from "@/components/NodeCard";
import { RecentEvents } from "@/components/RecentEvents";
import { StatTiles } from "@/components/StatTiles";
import { ActivityChart, type ActivityBar } from "@/components/charts/ActivityChart";
import { Gauge } from "@/components/charts/Gauge";
import { fetchEvents, fetchNodes } from "@/lib/api";
import type { EventInfo, NodeInfo } from "@/lib/types";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function buildActivity(events: EventInfo[]): ActivityBar[] {
  const counts = new Array(7).fill(0);
  for (const e of events) {
    const d = new Date(e.timestamp).getDay();
    counts[d] += 1;
  }
  return DAYS.map((label, i) => ({ label, value: counts[i] }));
}

function topClasses(events: EventInfo[]): { label: string; pct: number }[] {
  const counts: Record<string, number> = {};
  let total = 0;
  for (const e of events)
    for (const d of e.detections) {
      counts[d.label] = (counts[d.label] ?? 0) + 1;
      total += 1;
    }
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([label, n]) => ({ label, pct: total ? Math.round((n / total) * 100) : 0 }));
}

function Dashboard() {
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [events, setEvents] = useState<EventInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = () =>
      Promise.all([fetchNodes(), fetchEvents({ limit: 100 })])
        .then(([n, e]) => {
          if (!active) return;
          setNodes(n);
          setEvents(e.items);
        })
        .catch(() => active && setNodes([]))
        .finally(() => active && setLoading(false));
    load();
    const interval = setInterval(load, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const activity = useMemo(() => buildActivity(events), [events]);
  const classes = useMemo(() => topClasses(events), [events]);
  const avgConfidence = useMemo(() => {
    const all = events.flatMap((e) => e.detections.map((d) => d.confidence));
    if (all.length === 0) return 0;
    return all.reduce((s, x) => s + x, 0) / all.length;
  }, [events]);

  return (
    <AppShell>
      <GreetingHeader />

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-5 lg:col-span-2">
          <StatTiles nodes={nodes} eventCount={events.length} />

          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {/* Confidence gauge */}
            <div className="card flex flex-col items-center p-5">
              <h2 className="mb-2 self-start text-sm font-semibold text-content">
                Avg Confidence
              </h2>
              <Gauge
                value={avgConfidence}
                display={`${(avgConfidence * 100).toFixed(0)}%`}
                label="across recent detections"
                size={180}
              />
              <div className="mt-3 w-full space-y-1.5">
                {classes.length === 0 ? (
                  <p className="text-center text-xs text-content-faint">No detections yet</p>
                ) : (
                  classes.map((c) => (
                    <div key={c.label} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-content-muted">
                        <span className="h-2 w-2 rounded-full bg-accent" />
                        {c.label}
                      </span>
                      <span className="font-mono text-content">{c.pct}%</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Activity chart */}
            <div className="card p-5 md:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-content">Detection Activity</h2>
                <span className="flex items-center gap-1.5 text-xs text-content-muted">
                  <span className="h-2 w-2 rounded-full bg-accent" /> Detections / day
                </span>
              </div>
              <ActivityChart data={activity} />
            </div>
          </div>

          {/* Fleet node cards */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-content">Fleet</h2>
            {loading ? (
              <p className="text-sm text-content-faint">Loading fleet…</p>
            ) : nodes.length === 0 ? (
              <p className="card p-8 text-center text-sm text-content-faint">
                No nodes registered yet. Start an edge agent to see it appear here.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {nodes.map((n) => (
                  <NodeCard key={n.node_id} node={n} />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <FleetStatusCard nodes={nodes} />
          <RecentEvents />
        </div>
      </div>
    </AppShell>
  );
}

export default function HomePage() {
  return (
    <AuthGuard>
      <Dashboard />
    </AuthGuard>
  );
}
