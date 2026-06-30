import { describe, expect, it, vi } from "vitest";

import { timeAgo } from "@/lib/utils";

describe("timeAgo", () => {
  it("formats seconds", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-30T12:00:30Z"));
    expect(timeAgo("2026-06-30T12:00:00Z")).toBe("30s ago");
    vi.useRealTimers();
  });

  it("formats minutes", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-30T12:05:00Z"));
    expect(timeAgo("2026-06-30T12:00:00Z")).toBe("5m ago");
    vi.useRealTimers();
  });

  it("formats hours", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-30T15:00:00Z"));
    expect(timeAgo("2026-06-30T12:00:00Z")).toBe("3h ago");
    vi.useRealTimers();
  });
});
