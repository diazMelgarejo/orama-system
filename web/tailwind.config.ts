import type { Config } from "tailwindcss";

// Operator console design tokens.
// Every colour is a CSS variable declared in src/styles/tokens.css, wrapped so
// opacity modifiers (bg-status-err/5, border-status-err/40, ...) keep working
// and so the light theme needs no Tailwind or component change. The names are
// unchanged on purpose: no component had to be edited for the theme work.
const channel = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Backgrounds: page, panels, cards, wells
        canvas: {
          DEFAULT: channel("canvas"),
          surface: channel("canvas-surface"),
          raised: channel("canvas-raised"),
          inset: channel("canvas-inset"),
        },
        // Borders + dividers
        line: {
          DEFAULT: channel("line"),
          strong: channel("line-strong"),
        },
        // Foreground
        ink: {
          DEFAULT: channel("ink"),
          muted: channel("ink-muted"),
          subtle: channel("ink-subtle"),
        },
        // Status
        status: {
          ok: channel("status-ok"),
          warn: channel("status-warn"),
          err: channel("status-err"),
          info: channel("status-info"),
          gpu: channel("status-gpu"),
        },
        // Accent (action / primary)
        accent: {
          DEFAULT: channel("accent"),
          hover: channel("accent-hover"),
          mute: channel("accent-mute"),
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        raised: "0 1px 0 0 rgba(0,0,0,0.6) inset, 0 1px 1px rgba(0,0,0,0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
