import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--bg-panel)",
        "panel-2": "var(--bg-panel-2)",
        border: "var(--border)",
        "border-hot": "var(--border-hot)",
        fg: "var(--text)",
        "fg-dim": "var(--text-dim)",
        "fg-faint": "var(--text-faint)",
        accent: "var(--accent)",
        up: "var(--green)",
        down: "var(--red)",
        amber: "var(--amber)",
        cyan: "var(--cyan)",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
