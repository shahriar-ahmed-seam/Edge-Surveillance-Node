"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { FleetStatusCard } from "@/components/FleetStatusCard";
import { NodeCard } from "@/components/NodeCard";
import { fetchNodes } from "@/lib/api";
import type { NodeInfo } from "@/lib/types";

function FleetView() {
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchNodes()
        .then((n) => active && setNodes(n))
        .catch(() => active && setNodes([]))
        .finally(() => active && setLoading(false));
    load();
    const interval = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-content">Fleet</h1>
        <p className="mt-1 text-sm text-content-muted">
          Health and telemetry for every edge node in your deployment.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {loading ? (
            <p className="text-sm text-content-faint">Loading fleet…</p>
          ) : nodes.length === 0 ? (
            <p className="card p-8 text-center text-sm text-content-faint">
              No nodes registered yet.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {nodes.map((n) => (
                <NodeCard key={n.node_id} node={n} />
              ))}
            </div>
          )}
        </div>
        <FleetStatusCard nodes={nodes} />
      </div>
    </AppShell>
  );
}

export default function FleetPage() {
  return (
    <AuthGuard>
      <FleetView />
    </AuthGuard>
  );
}
