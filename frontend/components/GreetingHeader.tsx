"use client";

import { useEffect, useState } from "react";

function greeting(d: Date): string {
  const h = d.getHours();
  if (h < 12) return "Good Morning";
  if (h < 18) return "Good Afternoon";
  return "Good Evening";
}

export function GreetingHeader({ name = "Operator" }: { name?: string }) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => setNow(new Date()), []);

  const dateStr = now
    ? now.toLocaleDateString(undefined, {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-content sm:text-[28px]">
        {now ? greeting(now) : "Welcome"} <span className="text-accent">{name}</span>
      </h1>
      <p className="mt-1 flex items-center gap-2 text-sm text-content-muted">
        <CalendarIcon className="h-4 w-4 text-content-faint" />
        {dateStr || "Loading…"}
      </p>
    </div>
  );
}

function CalendarIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <rect x="3" y="4.5" width="18" height="16" rx="2.5" />
      <path d="M3 9h18M8 3v3M16 3v3" strokeLinecap="round" />
    </svg>
  );
}
