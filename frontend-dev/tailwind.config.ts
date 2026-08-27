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
        // One restrained family for all application text.
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        // The serif token is reserved for the FAIR wordmark.
        serif: ["var(--font-remark)", "Georgia", "serif"],
        // Monospace for code
        mono: ["var(--font-geist-mono)", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
