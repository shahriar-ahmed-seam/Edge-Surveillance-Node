import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { getBrandAssets } from "@/lib/assets";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

const brand = getBrandAssets();

export const metadata: Metadata = {
  title: `${brand.name} — Fleet Console`,
  description:
    "Real-time edge surveillance fleet monitoring: quantized on-device detection, event-driven telemetry, and live alerts.",
  icons: brand.favicon ? { icon: brand.favicon } : undefined,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="app-bg min-h-screen antialiased">{children}</body>
    </html>
  );
}
