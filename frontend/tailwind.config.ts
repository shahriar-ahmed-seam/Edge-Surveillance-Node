import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep black-green fintech surfaces
        surface: {
          DEFAULT: "#060A06",
          raised: "#0C120C",
          overlay: "#121A12",
          border: "#1E2A1E",
        },
        content: {
          DEFAULT: "#EAF2EA",
          muted: "#8FA38F",
          faint: "#5C6E5C",
        },
        // Vibrant lime/emerald accent
        accent: {
          DEFAULT: "#3BE66B",
          bright: "#5CF77F",
          soft: "#1C7A3D",
          deep: "#0E3D1F",
        },
        status: {
          online: "#3BE66B",
          degraded: "#FBBF24",
          offline: "#6B7B6B",
          error: "#F87171",
        },
      },
      backgroundImage: {
        "tile-green": "linear-gradient(135deg, #18351F 0%, #0E1F13 100%)",
        "tile-bright": "linear-gradient(135deg, #2BBF57 0%, #166B30 100%)",
        "accent-glow":
          "radial-gradient(600px 200px at 50% 0%, rgba(59,230,107,0.12), transparent 70%)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        lg: "16px",
        xl: "22px",
        "2xl": "28px",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(59,230,107,0.45)" },
          "100%": { boxShadow: "0 0 0 7px rgba(59,230,107,0)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.25s ease-out",
        "pulse-ring": "pulse-ring 1.6s ease-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
