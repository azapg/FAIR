import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'FAIR Platform',
			description: 'Open-source platform for AI-powered grading systems',
			defaultLocale: 'en',
			locales: {
				en: {
					label: 'English',
					lang: 'en',
				},
				es: {
					label: 'Español',
					lang: 'es',
				},
			},
			logo: {
				src: './src/assets/logo.svg',
			},
			social: {
				github: 'https://github.com/azapg/FAIR',
			},
			sidebar: [
				{
					label: 'Getting Started',
					translations: {
						es: 'Comenzando',
					},
					autogenerate: { directory: 'getting-started' },
				},
				{
					label: 'Development',
					translations: {
						es: 'Desarrollo',
					},
					autogenerate: { directory: 'development' },
				},
			],
			customCss: [
				'./src/styles/custom.css',
			],
		}),
	],
});
