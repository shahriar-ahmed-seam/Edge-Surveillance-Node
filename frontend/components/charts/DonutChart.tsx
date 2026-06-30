"use client";

export interface DonutSlice {
  label: string;
  value: number;
  color: string;
}

interface Props {
  slices: DonutSlice[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerValue?: string;
}

/** Lightweight SVG donut chart. */
export function DonutChart({
  slices,
  size = 200,
  thickness = 26,
  centerLabel,
  centerValue,
}: Props) {
  const total = slices.reduce((s, x) => s + x.value, 0) || 1;
  const radius = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;
  const arcs = slices.map((slice) => {
    const fraction = slice.value / total;
    const dash = fraction * circumference;
    const arc = {
      ...slice,
      dashArray: `${dash} ${circumference - dash}`,
      dashOffset: -offset,
    };
    offset += dash;
    return arc;
  });

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#162316" strokeWidth={thickness} />
        {arcs.map((arc, i) => (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={arc.color}
            strokeWidth={thickness}
            strokeDasharray={arc.dashArray}
            strokeDashoffset={arc.dashOffset}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.6s ease, stroke-dashoffset 0.6s ease" }}
          />
        ))}
      </svg>
      {(centerLabel || centerValue) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {centerLabel && (
            <span className="text-[10px] uppercase tracking-wide text-content-faint">
              {centerLabel}
            </span>
          )}
          {centerValue && (
            <span className="font-mono text-2xl font-semibold text-content">{centerValue}</span>
          )}
        </div>
      )}
    </div>
  );
}
