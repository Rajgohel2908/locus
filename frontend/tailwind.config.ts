import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        obsidian: "#080808",
        absolute: "#050506",
        electric: "#C8F432", // LOCUS signature Neon Lime accent
        emerald: "#22C55E",
        amber: "#F59E0B",
        crimson: "#EF4444",
        fg: "#FAFAFA",
        muted: "#A1A1AA",
        carbon: "#0E0E10",
        graphite: "#1E1E22",
        slate: "#131316",
        locusBg: "#080808",
        locusLime: "#C8F432",
      },
      fontFamily: {
        heading: ["var(--font-sora)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        "locus-l": ["var(--font-locus-l)", "Niconne", "cursive"],
        "locus-serif": ["var(--font-locus-serif)", "Instrument Serif", "Georgia", "serif"],
        "locus-sans": ["var(--font-locus-sans)", "Satoshi", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "10px",
        card: "12px",
        chip: "8px",
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
        card: "0 4px 12px 0 rgba(0, 0, 0, 0.5)",
      },
    },
  },
  plugins: [],
};
export default config;

