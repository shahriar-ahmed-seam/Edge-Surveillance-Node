/** Brand asset resolver. */
export interface BrandAssets {
  logo: string | null;
  wordmark: string | null;
  hero: string | null;
  favicon: string | null;
  name: string;
  accent: string;
}

export function getBrandAssets(): BrandAssets {
  const orNull = (v?: string) => (v && v.trim().length > 0 ? v.trim() : null);
  return {
    logo: orNull(process.env.NEXT_PUBLIC_ASSET_LOGO),
    wordmark: orNull(process.env.NEXT_PUBLIC_ASSET_WORDMARK),
    hero: orNull(process.env.NEXT_PUBLIC_ASSET_HERO),
    favicon: orNull(process.env.NEXT_PUBLIC_ASSET_FAVICON),
    name: process.env.NEXT_PUBLIC_BRAND_NAME || "Edge-Surveillance-Node",
    accent: process.env.NEXT_PUBLIC_BRAND_ACCENT || "#3BE66B",
  };
}

export const hasRealAsset = (slot: string | null): boolean => slot !== null;
