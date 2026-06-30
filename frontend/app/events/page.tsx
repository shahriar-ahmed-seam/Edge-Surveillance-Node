"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { EventFeed } from "@/components/EventFeed";
import { fetchNodes } from "@/lib/api";
import type { NodeInfo } from "@/lib/types";

function EventsView() {
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  useEffect(() => {
    fetchNodes().then(setNodes).catch(() => setNodes([]));
  }, []);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-content">Detection Events</h1>
        <p className="mt-1 text-sm text-content-muted">
          Live stream of detections across your fleet, with filtering and snapshots.
        </p>
      </div>
      <EventFeed nodes={nodes} />
    </AppShell>
  );
}

export default function EventsPage() {
  return (
    <AuthGuard>
      <EventsView />
    </AuthGuard>
  );
}
