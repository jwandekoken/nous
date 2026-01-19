# Implementation Plan: Starlight Documentation Site

## Overview

Add a Starlight-based documentation site to the Nous monorepo at `apps/docs`.

**Starlight** is a documentation theme built on Astro, known for:
- Extremely fast builds and minimal JS shipped to browser
- Built-in search (Pagefind), dark mode, i18n support
- Markdown/MDX support with rich components
- Active maintenance by the Astro team

**Languages:** English (default) and Portuguese (pt-BR)

## Tasks Checklist

### Phase 1: Scaffold Starlight Project
- [x] Scaffold Starlight project in apps/docs using `pnpm create astro`
- [x] Run `pnpm install` from root to integrate with workspace

### Phase 2: Configure Turborepo Integration
- [x] Update `turbo.json` with build task configuration
- [x] Update root `package.json` with build script

### Phase 3: Configure Starlight
- [x] Configure `astro.config.mjs` with Nous branding, sidebar, and i18n

### Phase 4: Create Documentation Structure
- [x] Create documentation directory structure (with i18n folders) *(EN structure with placeholder content)*
- [ ] Create Getting Started docs (introduction, installation, quickstart) - EN *(placeholder files created)*
- [ ] Create Concepts docs (overview, entities, facts, sources, identifiers) - EN *(placeholder files created)*
- [ ] Create API Reference docs (assimilate, lookup, lookup-summary, authentication) - EN *(placeholder index only)*
- [ ] Create Guides docs (integrating-with-agents, self-hosting, memory-model) - EN *(placeholder index only)*
- [ ] Translate Getting Started docs to pt-BR
- [ ] Translate Concepts docs to pt-BR
- [ ] Translate API Reference docs to pt-BR
- [ ] Translate Guides docs to pt-BR

### Phase 5: Customize Appearance
- [x] Add logo asset to `src/assets/`
- [x] Add custom CSS for Nous branding

### Phase 6: Deployment Configuration (Cloudflare Pages)
- [ ] Create project in Cloudflare dashboard and connect Git repo
- [ ] Configure build settings (root directory, build command, output)
- [ ] Configure Build Watch Paths to only build on `apps/docs/*` changes
- [ ] Test deployment on push to main

### Phase 7: Testing & Verification
- [x] Test dev server and verify all pages render
- [ ] Test language switching works correctly
- [x] Test production build

## Prerequisites

- Node.js 18+ (already satisfied)
- pnpm 9.6.0 (already configured)
- Turborepo (already configured)

## Implementation Steps

### Phase 1: Scaffold Starlight Project

#### 1.1 Create the docs app

```bash
cd apps
pnpm create astro --template starlight --yes docs
```

This creates the base Starlight project with:
- `astro.config.mjs` - Main configuration
- `src/content.config.ts` - Content collections setup
- `src/content/docs/` - Documentation markdown files
- `package.json` - Dependencies

#### 1.2 Verify pnpm workspace integration

The new `apps/docs` folder is automatically included via `pnpm-workspace.yaml`:
```yaml
packages:
  - "apps/*"
```

Run from root:
```bash
pnpm install
```

### Phase 2: Configure Turborepo Integration

#### 2.1 Update turbo.json

Add `build` task for docs:

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "outputs": ["dist/**"]
    },
    "test": {
      "outputs": ["coverage/**"]
    },
    "lint": {},
    "install": {
      "cache": false
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

#### 2.2 Update root package.json

Add build script:

```json
{
  "scripts": {
    "install:all": "pnpm install && pnpm turbo install",
    "dev": "pnpm turbo dev",
    "build": "pnpm turbo build",
    "test": "pnpm turbo test",
    "lint": "pnpm turbo lint"
  }
}
```

### Phase 3: Configure Starlight

#### 3.1 Update astro.config.mjs

```javascript
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

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
      defaultLocale: 'root', // English as default without /en/ prefix
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
```

#### 3.2 Update content.config.ts for i18n

```typescript
import { defineCollection } from 'astro:content';
import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
};
```

### Phase 4: Create Documentation Structure

#### 4.1 Directory structure (Multilingual)

With `root` locale for English, English content lives directly in `src/content/docs/`, while pt-BR content lives in `src/content/docs/pt-br/`. Starlight automatically provides fallback to English when translations are missing.

```
apps/docs/
├── astro.config.mjs
├── package.json
├── tsconfig.json
├── src/
│   ├── assets/
│   │   └── logo.svg
│   ├── styles/
│   │   └── custom.css
│   ├── content/
│   │   ├── i18n/                            # UI string translations
│   │   │   └── pt-BR.json
│   │   └── docs/
│   │       ├── index.mdx                    # Landing page (EN)
│   │       ├── getting-started/
│   │       │   ├── introduction.md
│   │       │   ├── installation.md
│   │       │   └── quickstart.md
│   │       ├── concepts/
│   │       │   ├── overview.md
│   │       │   ├── entities.md
│   │       │   ├── facts.md
│   │       │   ├── sources.md
│   │       │   └── identifiers.md
│   │       ├── api-reference/
│   │       │   ├── index.md
│   │       │   ├── assimilate.md
│   │       │   ├── lookup.md
│   │       │   ├── lookup-summary.md
│   │       │   └── authentication.md
│   │       ├── guides/
│   │       │   ├── integrating-with-agents.md
│   │       │   ├── self-hosting.md
│   │       │   └── memory-model.md
│   │       └── pt-br/                       # Portuguese translations
│   │           ├── index.mdx
│   │           ├── getting-started/
│   │           │   ├── introduction.md
│   │           │   ├── installation.md
│   │           │   └── quickstart.md
│   │           ├── concepts/
│   │           │   ├── overview.md
│   │           │   ├── entities.md
│   │           │   ├── facts.md
│   │           │   ├── sources.md
│   │           │   └── identifiers.md
│   │           ├── api-reference/
│   │           │   ├── index.md
│   │           │   ├── assimilate.md
│   │           │   ├── lookup.md
│   │           │   ├── lookup-summary.md
│   │           │   └── authentication.md
│   │           └── guides/
│   │               ├── integrating-with-agents.md
│   │               ├── self-hosting.md
│   │               └── memory-model.md
│   └── content.config.ts
└── public/
    └── favicon.svg
```

#### 4.2 URL Structure

| Language | URL Pattern | Example |
|----------|-------------|---------|
| English (default) | `/docs/page` | `/getting-started/introduction` |
| Portuguese | `/pt-br/docs/page` | `/pt-br/getting-started/introduction` |

#### 4.2 Initial content files

Create placeholder/initial content for each documentation page. Content can be migrated from:
- Existing `apps/api/README.md`
- The meetup presentation (`docs/apresentacao-meetup-memoria-agentes.md`)
- Code comments and docstrings

### Phase 5: Customize Appearance

#### 5.1 Add custom CSS (optional)

Create `src/styles/custom.css`:

```css
:root {
  --sl-color-accent-low: #1e3a5f;
  --sl-color-accent: #3b82f6;
  --sl-color-accent-high: #93c5fd;
}
```

Reference in config:
```javascript
starlight({
  customCss: ['./src/styles/custom.css'],
  // ...
})
```

#### 5.2 Add logo

Place logo file at `src/assets/logo.svg` (or `.png`).

### Phase 6: Deployment Configuration (Cloudflare Pages)

#### 6.1 Create Project in Cloudflare Dashboard

1. Go to Cloudflare dashboard → **Workers & Pages** → **Create**
2. Select **Pages** → **Connect to Git**
3. Connect your GitHub repository (`jwandekoken/nous`)
4. Configure build settings:
   - **Project name:** `nous-docs`
   - **Production branch:** `main`
   - **Root directory:** `apps/docs`
   - **Framework preset:** Astro
   - **Build command:** `pnpm build`
   - **Build output directory:** `dist`
5. Click **Save and Deploy**

#### 6.2 Configure Build Watch Paths (Monorepo)

After project creation, configure to only build when `apps/docs` changes:

1. Go to project → **Settings** → **Build** → **Build watch paths**
2. Set **Include paths:** `apps/docs/*`
3. Set **Exclude paths:** (leave empty)
4. Save changes

This ensures pushes to `main` only trigger a docs build when files in `apps/docs/` are modified.

#### 6.3 Configure Branch Deployments (Optional)

To only deploy from `main` branch:

1. Go to project → **Settings** → **Build** → **Branch deployments**
2. Set **Production branch:** `main`
3. Disable preview deployments if not needed, or configure specific branches

#### 6.4 Important Notes

- **Custom 404:** Starlight includes a 404 page by default, which Cloudflare Pages will serve correctly
- **Auto Minify:** If you experience hydration issues, disable Cloudflare's Auto Minify setting in **Speed** → **Optimization**
- **Build System:** Requires Build System V2 (default for new projects)
- **pnpm:** Cloudflare Pages supports pnpm natively

### Phase 7: Testing & Verification

#### 7.1 Local development

```bash
# From root
pnpm dev

# Or specifically for docs
cd apps/docs && pnpm dev
```

Verify:
- [ ] Dev server starts on port 4321 (default)
- [ ] Sidebar navigation works
- [ ] Search functionality works
- [ ] Dark/light mode toggle works
- [ ] All pages render correctly
- [ ] Language switcher appears and works
- [ ] English pages accessible at root URLs (e.g., `/getting-started/introduction`)
- [ ] Portuguese pages accessible at `/pt-br/` URLs (e.g., `/pt-br/getting-started/introduction`)
- [ ] Fallback to English works when pt-BR translation is missing

#### 7.2 Production build

```bash
pnpm build
```

Verify:
- [ ] Build completes without errors
- [ ] Output in `apps/docs/dist/`
- [ ] Static files are generated correctly for both languages

## Documentation Content Plan

### Priority 1: Core Documentation (English)

| Page | Source | EN | pt-BR |
|------|--------|:--:|:-----:|
| Introduction | New + README | [ ] | [ ] |
| Installation | README | [ ] | [ ] |
| Quick Start | New | [ ] | [ ] |
| Concepts Overview | Meetup presentation | [ ] | [ ] |

### Priority 2: API Reference (English)

| Page | Source | EN | pt-BR |
|------|--------|:--:|:-----:|
| Assimilate | Code + docstrings | [ ] | [ ] |
| Lookup | Code + docstrings | [ ] | [ ] |
| Lookup Summary | Code + docstrings | [ ] | [ ] |
| Authentication | Code + docstrings | [ ] | [ ] |

### Priority 3: Guides (English)

| Page | Source | EN | pt-BR |
|------|--------|:--:|:-----:|
| Integrating with Agents | New | [ ] | [ ] |
| Self-hosting | docker-compose docs | [ ] | [ ] |
| Memory Model | Meetup presentation | [ ] | [ ] |

**Note:** English content should be written first, then translated to pt-BR. Starlight provides automatic fallback to English when translations are not yet available.

## Files to Modify

| File | Action |
|------|--------|
| `turbo.json` | Add `build` task |
| `package.json` (root) | Add `build` script |
| `apps/docs/*` | New directory (scaffold) |

## Estimated Effort

| Phase | Description |
|-------|-------------|
| Phase 1 | Scaffold project |
| Phase 2 | Turborepo integration |
| Phase 3 | Starlight configuration |
| Phase 4 | Create doc structure |
| Phase 5 | Customize appearance |
| Phase 6 | Deployment config |
| Phase 7 | Testing |

## Commands Summary

```bash
# 1. Scaffold
cd apps && pnpm create astro --template starlight --yes docs

# 2. Install dependencies
cd .. && pnpm install

# 3. Run dev server
pnpm dev

# 4. Build for production
pnpm build
```

## References

- [Starlight Documentation](https://starlight.astro.build/)
- [Starlight i18n Guide](https://starlight.astro.build/guides/i18n/)
- [Astro Documentation](https://docs.astro.build/)
- [Starlight Configuration Reference](https://starlight.astro.build/reference/configuration/)
