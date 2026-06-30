# Operator Dashboard

Modern Next.js 14 (App Router + TypeScript) console for the Edge-Surveillance-Node
fleet. Real-time detection feed over WebSocket, fleet health, and node detail
views with a restrained, enterprise-grade design system.

## Develop

```bash
npm install
cp .env.example .env.local   # set API + WS URLs
npm run dev                  # http://localhost:3000
```

## Test

```bash
npm run test
```

## Build

```bash
npm run build && npm start
```

## Branding assets

The dashboard renders professional neutral placeholders until brand assets are
supplied via environment variables (then they apply on next build/load):

| Variable | Slot |
|---|---|
| `NEXT_PUBLIC_ASSET_LOGO` | square logo mark |
| `NEXT_PUBLIC_ASSET_WORDMARK` | horizontal wordmark |
| `NEXT_PUBLIC_ASSET_HERO` | hero background image |
| `NEXT_PUBLIC_ASSET_FAVICON` | favicon |
| `NEXT_PUBLIC_BRAND_NAME` | product name text |
| `NEXT_PUBLIC_BRAND_ACCENT` | accent hex color |

## Deploy (Vercel)

Set the root directory to `frontend/`, framework preset Next.js, and configure
the `NEXT_PUBLIC_*` environment variables. See [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).
