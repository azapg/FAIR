# FAIR Platform Documentation

This directory contains the documentation for FAIR Platform, built with [Astro Starlight](https://starlight.astro.build/).

## Features

- **i18n Support**: Documentation available in English and Spanish
- **Platform-Matching Design**: Uses the same fonts (Host Grotesk, Remark) and color scheme (oklch) as the main platform
- **Static Site Generation**: Fast, lightweight documentation with search functionality
- **Automatic Sidebar**: Auto-generated navigation from content structure

## Development

### Prerequisites

- [Bun](https://bun.sh) - Package manager and runtime

### Install Dependencies

```bash
bun install
```

### Development Server

```bash
bun run dev
```

The documentation will be available at `http://localhost:4321/en/` (English) or `http://localhost:4321/es/` (Spanish).

### Build

```bash
bun run build
```

The static site will be generated in the `dist/` directory.

### Preview Build

```bash
bun run preview
```

## Content Structure

```
src/content/docs/
├── en/                          # English content
│   ├── index.md                 # Homepage
│   ├── getting-started/
│   │   └── installation.md
│   └── development/
│       └── releases.md
└── es/                          # Spanish content
    ├── index.md
    ├── getting-started/
    │   └── installation.md
    └── development/
        └── releases.md
```

## Adding New Pages

1. Create a markdown file in the appropriate language directory
2. Add frontmatter with `title` and `description`
3. The sidebar will be auto-generated based on the directory structure

## Customization

- **Colors**: Edit `src/styles/custom.css` to adjust the color scheme
- **Fonts**: Fonts are copied from `../frontend-dev/public/fonts/` and loaded via `custom.css`
- **Logo**: Update `src/assets/logo.svg` to change the site logo
- **Configuration**: Edit `astro.config.mjs` for site-wide settings

## Technologies

- **Astro**: Static site generator
- **Starlight**: Documentation theme with built-in i18n, search, and more
- **Bun**: Fast JavaScript runtime and package manager
