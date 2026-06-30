"use client";

export interface BarItem {
  label: string;
  value: number;
  sublabel?: string;
}

/** Horizontal bar breakdown (e.g. detections by class or by node). */
export function HorizontalBars({ items, valueFormat }: { items: BarItem[]; valueFormat?: (v: number) => string }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  const fmt = valueFormat ?? ((v: number) => String(v));

  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-content-faint">No data yet.</p>;
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.label}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="truncate text-content">
              {item.label}
              {item.sublabel && <span className="ml-1 text-content-faint">{item.sublabel}</span>}
            </span>
            <span className="font-mono text-content-muted">{fmt(item.value)}</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-overlay">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(item.value / max) * 100}%`,
                background: "linear-gradient(90deg, #166B30 0%, #3BE66B 100%)",
                transition: "width 0.5s ease",
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
