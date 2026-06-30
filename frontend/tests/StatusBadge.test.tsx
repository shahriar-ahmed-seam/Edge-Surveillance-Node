import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("renders Online for healthy", () => {
    render(<StatusBadge status="healthy" />);
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("renders Degraded", () => {
    render(<StatusBadge status="degraded" />);
    expect(screen.getByText("Degraded")).toBeInTheDocument();
  });

  it("renders Offline", () => {
    render(<StatusBadge status="offline" />);
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});
