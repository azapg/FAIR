import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";

// https://astro.build/config
export default defineConfig({
  redirects: {
    '/': '/en'
  },
  integrations: [
    starlight({
      title: "FAIR Platform",
      description: "Open-source platform for AI-powered grading systems",
      defaultLocale: "en",
      locales: {
        en: {
          label: "English",
          lang: "en",
        },
        es: {
          label: "Español",
          lang: "es",
        },
      },
      social: {
        github: "https://github.com/azapg/FAIR",
      },
      sidebar: [
        {
          label: "Getting Started",
          translations: {
            es: "Comenzando",
          },
          autogenerate: { directory: "getting-started" },
        },
        {
          label: "Development",
          translations: {
            es: "Desarrollo",
          },
          autogenerate: { directory: "development" },
        },
      ],
      customCss: ["./src/styles/custom.css"],
      components: {
        SiteTitle: "./src/components/header-title.astro",
        ThemeSelect: "./src/components/theme-select.astro",
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
