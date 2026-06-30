"use client";

export interface ActivityBar {
  label: string;
  value: number;
}

/** Weekly activity bar chart. */
export function ActivityChart({ data, height = 220 }: { data: ActivityBar[]; height?: number }) {
  const max = Math.max(1, ...data.map((d) => d.value));

  return (
    <div className="w-full">
      <div className="flex items-end justify-between gap-2" style={{ height }}>
        {data.map((d) => {
          const h = Math.round((d.value / max) * (height - 28));
          return (
            <div key={d.label} className="flex flex-1 flex-col items-center justify-end gap-2">
              <span className="font-mono text-[10px] text-content-muted">{d.value}</span>
              <div
                className="w-full max-w-[34px] rounded-t-md"
                style={{
                  height: `${Math.max(4, h)}px`,
                  background: "linear-gradient(180deg, #5CF77F 0%, #1C7A3D 100%)",
                  transition: "height 0.5s ease",
                }}
              />
              <span className="text-[10px] text-content-faint">{d.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
