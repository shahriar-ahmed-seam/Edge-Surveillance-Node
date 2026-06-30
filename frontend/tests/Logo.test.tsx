import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Logo } from "@/components/brand/Logo";

describe("Logo", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("renders the placeholder mark when no logo asset is configured", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_LOGO", "");
    render(<Logo />);
    expect(screen.getByTestId("placeholder-logo")).toBeInTheDocument();
  });

  it("renders the supplied logo image when configured", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_LOGO", "https://cdn.example.com/logo.svg");
    render(<Logo />);
    const img = screen.getByAltText(/logo/i) as HTMLImageElement;
    expect(img.src).toContain("cdn.example.com/logo.svg");
    expect(screen.queryByTestId("placeholder-logo")).not.toBeInTheDocument();
  });

  it("shows the brand name as wordmark fallback", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_WORDMARK", "");
    vi.stubEnv("NEXT_PUBLIC_BRAND_NAME", "Acme Vision");
    render(<Logo withWordmark />);
    expect(screen.getByText("Acme Vision")).toBeInTheDocument();
  });
});
