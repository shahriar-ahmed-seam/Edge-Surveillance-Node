"use client";

import type { NodeInfo } from "@/lib/types";

export interface FilterValue {
  node_id: string;
  label: string;
  since: string;
}

interface Props {
  nodes: NodeInfo[];
  value: FilterValue;
  onChange: (value: FilterValue) => void;
}

export function Filters({ nodes, value, onChange }: Props) {
  const set = (patch: Partial<FilterValue>) => onChange({ ...value, ...patch });

  return (
    <div className="flex flex-wrap items-end gap-3">
      <Field label="Node">
        <select
          className="input"
          value={value.node_id}
          onChange={(e) => set({ node_id: e.target.value })}
        >
          <option value="">All nodes</option>
          {nodes.map((n) => (
            <option key={n.node_id} value={n.node_id}>
              {n.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Class">
        <input
          className="input"
          placeholder="e.g. person"
          value={value.label}
          onChange={(e) => set({ label: e.target.value })}
        />
      </Field>
      <Field label="Since">
        <input
          className="input"
          type="datetime-local"
          value={value.since}
          onChange={(e) => set({ since: e.target.value })}
        />
      </Field>
      {(value.node_id || value.label || value.since) && (
        <button
          className="h-9 rounded-md border border-surface-border px-3 text-xs text-content-muted hover:text-content"
          onClick={() => onChange({ node_id: "", label: "", since: "" })}
        >
          Clear
        </button>
      )}
      <style jsx>{`
        :global(.input) {
          height: 2.25rem;
          border-radius: 0.5rem;
          border: 1px solid #1f2730;
          background: #161c24;
          padding: 0 0.625rem;
          font-size: 0.8125rem;
          color: #e6eaf0;
          min-width: 9rem;
        }
        :global(.input:focus) {
          outline: none;
          border-color: rgba(34, 211, 238, 0.5);
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wide text-content-faint">{label}</span>
      {children}
    </label>
  );
}
