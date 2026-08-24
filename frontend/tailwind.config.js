/**
 * Design System ComptaFlow — tokens premium
 * ------------------------------------------------------------------
 * Palette : indigo profond (confiance + finance), neutres ardoise tiédis.
 * Typo    : Plus Jakarta Sans (titres), Inter (corps).
 * Esprit  : haut de gamme, sobre, rassurant pour des experts-comptables.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Couleur de marque — indigo riche, échelle complète
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5", // primaire
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        // Accent secondaire — violet lumineux pour les dégradés/highlights
        accent: {
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
        },
        // Neutres ardoise légèrement tiédis (plus chics que gray pur)
        ink: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
          950: "#020617",
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Échelle resserrée pour les gros titres
        "display-sm": ["2.5rem", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "display-md": ["3.25rem", { lineHeight: "1.05", letterSpacing: "-0.025em" }],
        "display-lg": ["4.25rem", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
      },
      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
      },
      boxShadow: {
        // Ombres douces et étagées (style premium, pas de noir dur)
        soft: "0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)",
        card: "0 4px 12px -2px rgba(15,23,42,0.06), 0 2px 6px -2px rgba(15,23,42,0.04)",
        elevated: "0 12px 32px -8px rgba(15,23,42,0.12), 0 6px 16px -8px rgba(15,23,42,0.08)",
        float: "0 24px 48px -12px rgba(30,27,75,0.18), 0 12px 24px -12px rgba(30,27,75,0.10)",
        glow: "0 0 0 1px rgba(79,70,229,0.10), 0 8px 32px -8px rgba(79,70,229,0.35)",
        "glow-lg": "0 0 0 1px rgba(79,70,229,0.12), 0 20px 60px -12px rgba(79,70,229,0.45)",
        "inner-light": "inset 0 1px 0 0 rgba(255,255,255,0.6)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #a855f7 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%)",
        "mesh": "radial-gradient(at 20% 20%, rgba(99,102,241,0.18) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(168,85,247,0.14) 0px, transparent 50%), radial-gradient(at 80% 80%, rgba(79,70,229,0.12) 0px, transparent 50%)",
        "grid": "linear-gradient(to right, rgba(15,23,42,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(15,23,42,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "44px 44px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        "gradient-x": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.16,1,0.3,1) both",
        "fade-in": "fade-in 0.5s ease-out both",
        "scale-in": "scale-in 0.4s cubic-bezier(0.16,1,0.3,1) both",
        float: "float 6s ease-in-out infinite",
        "gradient-x": "gradient-x 6s ease infinite",
      },
    },
  },
  plugins: [],
};
