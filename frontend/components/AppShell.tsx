"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearSession, getRole } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Logo } from "./brand/Logo";

const NAV = [
  { href: "/", label: "Dashboard", icon: GridIcon },
  { href: "/fleet", label: "Fleet", icon: NodesIcon },
  { href: "/events", label: "Events", icon: PulseIcon },
  { href: "/analytics", label: "Analytics", icon: ChartIcon },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const role = getRole();

  const logout = () => {
    clearSession();
    router.replace("/login");
  };

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <div className="mx-auto min-h-screen max-w-[1400px] px-4 py-5 sm:px-6">
      {/* Top bar */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <Logo size={36} />
          <div className="leading-tight">
            <div className="text-base font-semibold tracking-tight text-content">
              Edge<span className="text-accent">Surveillance</span>
            </div>
            <div className="text-[11px] text-content-faint">Fleet intelligence, on the edge.</div>
          </div>
        </Link>

        <nav className="order-3 flex items-center gap-1 rounded-full border border-surface-border bg-surface-raised p-1 sm:order-2">
          {NAV.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "pill",
                  active
                    ? "bg-accent text-surface shadow-[0_0_20px_rgba(59,230,107,0.35)]"
                    : "text-content-muted hover:text-content"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="order-2 flex items-center gap-2 sm:order-3">
          <button
            className="grid h-10 w-10 place-items-center rounded-full border border-surface-border bg-surface-raised text-content-muted transition-colors hover:text-content"
            aria-label="Notifications"
          >
            <BellIcon className="h-4.5 w-4.5" />
          </button>
          <div className="flex items-center gap-2 rounded-full border border-surface-border bg-surface-raised py-1 pl-1 pr-3">
            <div className="grid h-8 w-8 place-items-center rounded-full bg-tile-bright text-sm font-semibold text-surface">
              {(role ?? "op").slice(0, 1).toUpperCase()}
            </div>
            <button onClick={logout} className="text-xs text-content-muted hover:text-content">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="py-6">{children}</main>

      <footer className="border-t border-surface-border py-4 text-center text-xs text-content-faint">
        Edge-Surveillance-Node · Fleet Console
      </footer>
    </div>
  );
}

/* --- inline icons (no extra deps) --- */
function GridIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}
function NodesIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="12" cy="18" r="2.5" />
      <path d="M7.7 7.7 11 15M16.3 7.7 13 15" />
    </svg>
  );
}
function PulseIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M3 12h4l2 6 4-14 2 8h6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function ChartIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M4 20V4M4 20h16" strokeLinecap="round" />
      <rect x="7" y="12" width="3" height="5" rx="0.5" />
      <rect x="12" y="8" width="3" height="9" rx="0.5" />
      <rect x="17" y="5" width="3" height="12" rx="0.5" />
    </svg>
  );
}
function BellIcon(p: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 19a2 2 0 0 0 4 0" strokeLinecap="round" />
    </svg>
  );
}
