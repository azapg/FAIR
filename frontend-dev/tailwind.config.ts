import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Default body font - Host Grotesk
        sans: ["var(--font-host-grotesk)", "system-ui", "sans-serif"],
        // Headings font - Remark
        serif: ["var(--font-remark)", "Georgia", "serif"],
        // Monospace for code
        mono: ["var(--font-geist-mono)", "Consolas", "monospace"],
        // Explicit font families for granular control
        "host-grotesk": ["var(--font-host-grotesk)", "sans-serif"],
        remark: ["var(--font-remark)", "serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
