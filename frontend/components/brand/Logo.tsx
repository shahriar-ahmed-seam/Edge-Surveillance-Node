import { getBrandAssets } from "@/lib/assets";
import { cn } from "@/lib/utils";

interface LogoProps {
  size?: number;
  withWordmark?: boolean;
  className?: string;
}

export function Logo({ size = 32, withWordmark = false, className }: LogoProps) {
  const assets = getBrandAssets();

  const mark = assets.logo ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={assets.logo} alt={`${assets.name} logo`} width={size} height={size} />
  ) : (
    <PlaceholderMark size={size} accent={assets.accent} />
  );

  return (
    <div className={cn("flex items-center gap-2.5", className)} data-testid="brand-logo">
      {mark}
      {withWordmark &&
        (assets.wordmark ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={assets.wordmark} alt={assets.name} height={size} />
        ) : (
          <span className="text-[15px] font-semibold tracking-tight text-content">
            {assets.name}
          </span>
        ))}
    </div>
  );
}

function PlaceholderMark({ size, accent }: { size: number; accent: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="placeholder logo"
      data-testid="placeholder-logo"
    >
      <rect x="1" y="1" width="30" height="30" rx="8" fill="#0C120C" stroke="#1E2A1E" />
      {/* aperture / node motif */}
      <circle cx="16" cy="16" r="7" stroke={accent} strokeWidth="2" />
      <circle cx="16" cy="16" r="2.5" fill={accent} />
      <path d="M16 4v4M16 24v4M4 16h4M24 16h4" stroke={accent} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
