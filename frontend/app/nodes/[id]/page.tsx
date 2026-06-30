"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { EventFeed } from "@/components/EventFeed";
import { NodeAnalytics } from "@/components/NodeAnalytics";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchNode } from "@/lib/api";
import type { NodeInfo } from "@/lib/types";
import { localTime } from "@/lib/utils";

function metric(node: NodeInfo, key: string): string {
  const v = node.last_metrics?.[key];
  return v === undefined || v === null ? "—" : String(v);
}

function NodeDetail({ id }: { id: string }) {
  const [node, setNode] = useState<NodeInfo | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchNode(id)
        .then((n) => active && setNode(n))
        .catch(() => active && setNotFound(true));
    load();
    const interval = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [id]);

  if (notFound) {
    return (
      <AppShell>
        <p className="text-sm text-content-muted">
          Node not found.{" "}
          <Link href="/" className="text-accent">
            Back to fleet
          </Link>
        </p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Link href="/" className="text-xs text-content-muted hover:text-content">
        ← Fleet
      </Link>
      {node && (
        <div className="mt-4 space-y-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-content">{node.name}</h1>
              <p className="font-mono text-sm text-content-faint">{node.node_id}</p>
            </div>
            <StatusBadge status={node.status} />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="FPS" value={metric(node, "fps")} />
            <Metric label="Inference" value={metric(node, "inference_ms")} unit="ms" />
            <Metric label="Queue Depth" value={metric(node, "queue_depth")} />
            <Metric label="Connection" value={metric(node, "connection")} />
          </div>

          <div className="card p-4 text-sm text-content-muted">
            <div className="flex justify-between py-1">
              <span>First seen</span>
              <span className="font-mono">{localTime(node.first_seen)}</span>
            </div>
            <div className="flex justify-between py-1">
              <span>Last seen</span>
              <span className="font-mono">{localTime(node.last_seen)}</span>
            </div>
            <div className="flex justify-between py-1">
              <span>State</span>
              <span className="font-mono">{metric(node, "state")}</span>
            </div>
          </div>

          <NodeAnalytics nodeId={node.node_id} />

          <EventFeed nodes={[node]} nodeId={node.node_id} />
        </div>
      )}
    </AppShell>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-content-faint">{label}</div>
      <div className="mt-1.5 font-mono text-xl text-content">
        {value}
        {unit && value !== "—" ? <span className="text-content-faint"> {unit}</span> : null}
      </div>
    </div>
  );
}

export default function NodePage({ params }: { params: { id: string } }) {
  return (
    <AuthGuard>
      <NodeDetail id={decodeURIComponent(params.id)} />
    </AuthGuard>
  );
}
