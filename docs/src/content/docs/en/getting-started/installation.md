---
title: Installation
description: How to install and set up FAIR Platform
---

# Installation

This guide will help you install and set up FAIR Platform on your system.

## Requirements

Before installing FAIR Platform, make sure you have the following:

- **Python 3.12+** - Required for running the platform
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Python package installer and resolver
- **[Bun](https://bun.com/get)** - For frontend development (optional)

## Quick Installation

The simplest way to install FAIR Platform is using pip:

```bash
pip install fair-platform
```

## Running the Platform

Once installed, you can start the platform with:

```bash
fair serve
```

The platform will be available at `http://localhost:8000` by default.

### Command Options

```bash
# Specify a custom port
fair serve --port 3000

# Development mode with CORS enabled
fair serve --dev

# Headless mode (API only, no frontend)
fair serve --headless
```

## Development Installation

For development work on the platform itself:

### 1. Clone the Repository

```bash
git clone https://github.com/azapg/FAIR.git
cd FAIR
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Build the Frontend

```bash
./build.sh
```

This script will:
1. Build the frontend assets using Vite
2. Copy the built files to the Python package
3. Build the Python package

### 4. Run the Development Server

```bash
fair serve --dev
```

## Frontend Development

If you're working on the frontend only:

```bash
cd frontend-dev
bun install
bun run dev
```

The frontend development server will run on port 3000 and proxy API calls to the backend on port 8000.

## Database Configuration

By default, FAIR Platform uses SQLite. To use PostgreSQL:

```bash
export DATABASE_URL="postgresql://user:password@localhost/dbname"
fair serve
```

## Next Steps

- Explore the [platform features](/)
- Learn about the [release process](/development/releases)
- Start building your own grading modules

## Troubleshooting

### Python Version Issues

Make sure you're using Python 3.12 or higher:

```bash
python --version
```

### Build Errors

If the build fails, ensure you have all dependencies installed:

```bash
# Reinstall dependencies
uv sync

# Clean and rebuild
rm -rf frontend-dev/dist
./build.sh
```

### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
fair serve --port 8080
```
