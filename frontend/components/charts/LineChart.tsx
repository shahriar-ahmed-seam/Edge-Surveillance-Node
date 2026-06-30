"use client";

import { useId } from "react";

export interface LineSeries {
  values: number[];
  color: string;
  fill?: boolean;
}

interface Props {
  series: LineSeries[];
  labels: string[];
  height?: number;
  valueSuffix?: string;
}

/** Minimal responsive SVG area/line chart supporting multiple overlaid series. */
export function LineChart({ series, labels, height = 240, valueSuffix = "" }: Props) {
  const gid = useId().replace(/:/g, "");
  const width = 720;
  const padX = 36;
  const padY = 24;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const n = Math.max(1, labels.length - 1);

  const x = (i: number) => padX + (i / n) * innerW;
  const y = (v: number) => padY + innerH - (v / max) * innerH;

  const linePath = (vals: number[]) =>
    vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");

  const areaPath = (vals: number[]) =>
    `${linePath(vals)} L ${x(vals.length - 1).toFixed(1)} ${padY + innerH} L ${x(0).toFixed(1)} ${
      padY + innerH
    } Z`;

  const gridLines = 4;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img">
      <defs>
        {series.map((s, i) => (
          <linearGradient key={i} id={`${gid}-fill-${i}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={s.color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={s.color} stopOpacity="0" />
          </linearGradient>
        ))}
      </defs>

      {/* horizontal grid */}
      {Array.from({ length: gridLines + 1 }).map((_, i) => {
        const gy = padY + (i / gridLines) * innerH;
        const val = Math.round(max - (i / gridLines) * max);
        return (
          <g key={i}>
            <line x1={padX} y1={gy} x2={width - padX} y2={gy} stroke="#1A271A" strokeWidth="1" />
            <text x={8} y={gy + 3} fontSize="9" fill="#5C6E5C">
              {val}
            </text>
          </g>
        );
      })}

      {/* series */}
      {series.map((s, i) => (
        <g key={i}>
          {s.fill && <path d={areaPath(s.values)} fill={`url(#${gid}-fill-${i})`} />}
          <path
            d={linePath(s.values)}
            fill="none"
            stroke={s.color}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {s.values.map((v, j) => (
            <circle key={j} cx={x(j)} cy={y(v)} r="2.5" fill={s.color} />
          ))}
        </g>
      ))}

      {/* x labels */}
      {labels.map((lab, i) => (
        <text key={i} x={x(i)} y={height - 6} fontSize="9" fill="#5C6E5C" textAnchor="middle">
          {lab}
        </text>
      ))}
    </svg>
  );
}
