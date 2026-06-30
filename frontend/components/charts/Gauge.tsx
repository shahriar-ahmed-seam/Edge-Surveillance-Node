"use client";

interface Props {
  /** 0..1 fraction filled */
  value: number;
  size?: number;
  thickness?: number;
  label?: string;
  display?: string;
}

/** Half-circle gauge. */
export function Gauge({ value, size = 200, thickness = 22, label, display }: Props) {
  const clamped = Math.max(0, Math.min(1, value));
  const radius = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;
  // Semicircle: 180deg sweep from left (180) to right (360/0).
  const arcLength = Math.PI * radius;
  const dash = clamped * arcLength;

  const describeArc = () => {
    const start = polar(cx, cy, radius, 180);
    const end = polar(cx, cy, radius, 360);
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`;
  };

  return (
    <div className="relative inline-flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size / 2 + thickness} viewBox={`0 0 ${size} ${size / 2 + thickness}`}>
        <defs>
          <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#166B30" />
            <stop offset="60%" stopColor="#3BE66B" />
            <stop offset="100%" stopColor="#5CF77F" />
          </linearGradient>
        </defs>
        <path d={describeArc()} fill="none" stroke="#162316" strokeWidth={thickness} strokeLinecap="round" />
        <path
          d={describeArc()}
          fill="none"
          stroke="url(#gauge-grad)"
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${arcLength - dash}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="-mt-8 flex flex-col items-center">
        <span className="font-mono text-2xl font-semibold text-content">{display}</span>
        {label && <span className="mt-0.5 text-xs text-content-muted">{label}</span>}
      </div>
    </div>
  );
}

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const a = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}
