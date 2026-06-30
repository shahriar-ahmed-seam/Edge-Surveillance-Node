import { afterEach, describe, expect, it, vi } from "vitest";

import { getBrandAssets, hasRealAsset } from "@/lib/assets";

describe("brand asset resolver", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns null slots and default name when no assets configured", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_LOGO", "");
    vi.stubEnv("NEXT_PUBLIC_BRAND_NAME", "");
    const a = getBrandAssets();
    expect(a.logo).toBeNull();
    expect(a.hero).toBeNull();
    expect(a.name).toBe("Edge-Surveillance-Node");
    expect(hasRealAsset(a.logo)).toBe(false);
  });

  it("uses supplied asset URLs when configured", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_LOGO", "https://cdn.example.com/logo.svg");
    vi.stubEnv("NEXT_PUBLIC_BRAND_NAME", "Acme Vision");
    const a = getBrandAssets();
    expect(a.logo).toBe("https://cdn.example.com/logo.svg");
    expect(a.name).toBe("Acme Vision");
    expect(hasRealAsset(a.logo)).toBe(true);
  });

  it("treats whitespace-only values as unset", () => {
    vi.stubEnv("NEXT_PUBLIC_ASSET_HERO", "   ");
    expect(getBrandAssets().hero).toBeNull();
  });
});
