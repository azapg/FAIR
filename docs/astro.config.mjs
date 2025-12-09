import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";
import react from '@astrojs/react';


// https://astro.build/config
export default defineConfig({
  redirects: {
    '/': '/en/introduction',
    '/en': '/en/introduction',
    '/es': '/es/introduction'
  },
  integrations: [
    react(),
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
          slug: "introduction",
          label: "Introduction",
          translations: {
            es: "Introducción"
          }
        },
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
      customCss: ["./src/styles/custom.css", "./src/styles/fonts.css"],
      components: {
        SiteTitle: "./src/components/header-title.astro",
        PageTitle: "./src/components/page-title.astro",
        ContentPanel: "./src/components/content-panel.astro",
        ThemeSelect: "./src/components/theme-select.astro",
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
