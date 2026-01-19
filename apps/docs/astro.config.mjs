// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'Nous',
			description: 'Knowledge Graph Memory for AI Agents',
			logo: {
				src: './src/assets/logo.svg',
			},
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/jwandekoken/nous' },
			],
			// Internationalization configuration
			defaultLocale: 'root',
			locales: {
				root: {
					label: 'English',
					lang: 'en',
				},
				'pt-br': {
					label: 'Português (Brasil)',
					lang: 'pt-BR',
				},
			},
			sidebar: [
				{
					label: 'Getting Started',
					translations: { 'pt-BR': 'Primeiros Passos' },
					items: [
						{ label: 'Introduction', slug: 'getting-started/introduction' },
						{ label: 'Installation', slug: 'getting-started/installation' },
						{ label: 'Quick Start', slug: 'getting-started/quickstart' },
					],
				},
				{
					label: 'Concepts',
					translations: { 'pt-BR': 'Conceitos' },
					items: [
						{ label: 'Overview', slug: 'concepts/overview' },
						{ label: 'Entities', slug: 'concepts/entities' },
						{ label: 'Facts', slug: 'concepts/facts' },
						{ label: 'Sources', slug: 'concepts/sources' },
						{ label: 'Identifiers', slug: 'concepts/identifiers' },
					],
				},
				{
					label: 'API Reference',
					translations: { 'pt-BR': 'Referência da API' },
					autogenerate: { directory: 'api-reference' },
				},
				{
					label: 'Guides',
					translations: { 'pt-BR': 'Guias' },
					autogenerate: { directory: 'guides' },
				},
			],
			editLink: {
				baseUrl: 'https://github.com/jwandekoken/nous/edit/main/apps/docs/',
			},
			lastUpdated: true,
			customCss: ['./src/styles/custom.css'],
		}),
	],
});
