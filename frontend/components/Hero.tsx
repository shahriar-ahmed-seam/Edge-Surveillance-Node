import { getBrandAssets } from "@/lib/assets";

export function Hero({ title, subtitle }: { title: string; subtitle: string }) {
  const assets = getBrandAssets();

  return (
    <section className="relative overflow-hidden rounded-xl border border-surface-border bg-surface-raised">
      {assets.hero ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={assets.hero}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-40"
        />
      ) : (
        <PlaceholderHero accent={assets.accent} />
      )}
      <div className="relative z-10 px-6 py-10 sm:px-10 sm:py-14">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-accent">
          Fleet Operations
        </p>
        <h1 className="max-w-2xl text-2xl font-semibold tracking-tight text-content sm:text-3xl">
          {title}
        </h1>
        <p className="mt-3 max-w-xl text-sm text-content-muted">{subtitle}</p>
      </div>
    </section>
  );
}

function PlaceholderHero({ accent }: { accent: string }) {
  return (
    <div
      aria-hidden
      className="absolute inset-0"
      style={{
        background:
          "radial-gradient(900px 300px at 12% -10%, rgba(34,211,238,0.14), transparent 60%), radial-gradient(700px 320px at 90% 120%, rgba(14,116,144,0.18), transparent 55%)",
      }}
      data-testid="placeholder-hero"
    >
      <div className="bg-grid absolute inset-0 opacity-60" />
    </div>
  );
}
