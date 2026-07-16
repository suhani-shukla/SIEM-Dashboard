// FILE LOCATION: frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          bg: "#0A0E14",
          surface: "#111720",
          "surface-raised": "#171F2A",
          hover: "#1C2531",
          border: "#232C38",
          "border-strong": "#31404F",
        },
        ink: {
          primary: "#E6EDF3",
          secondary: "#9AA7B4",
          muted: "#5E6B78",
        },
        brand: {
          DEFAULT: "#2DD4BF",
          dim: "#0F766E",
          glow: "#5EEAD4",
        },
        severity: {
          info: "#64748B",
          low: "#3B82F6",
          medium: "#EAB308",
          high: "#F97316",
          critical: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(45,212,191,0.35), 0 0 16px rgba(45,212,191,0.25)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.4, transform: "scale(0.85)" },
        },
        flashIn: {
          "0%": { backgroundColor: "rgba(45,212,191,0.18)" },
          "100%": { backgroundColor: "transparent" },
        },
      },
      animation: {
        "pulse-dot": "pulseDot 1.6s ease-in-out infinite",
        "flash-in": "flashIn 1.8s ease-out",
      },
    },
  },
  plugins: [],
};
