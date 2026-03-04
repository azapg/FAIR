---
title: CLI Reference
description: Manage your FAIR instance directly from the terminal.
---

The `fair` Command Line Interface (CLI) is the primary tool for starting the platform, managing your database, and developing new features.

## Installation

The CLI is included with the `fair-platform` package. If you haven't installed it yet, run:

```bash
pip install fair-platform
```

For more detailed setup instructions, including using `uv` or building from source, see our [Quickstart Guide](/en/quickstart).

## Primary Commands

### Starting the Platform
To run the platform in production mode (using the built-in frontend):

```bash
fair serve
```

<ParamField query="--port" type="integer" default="3000">
  The port to run the server on. Use `-p` as a shorthand.
</ParamField>

<ParamField query="--headless" type="boolean" default="false">
  Start only the backend API without any frontend assets. Use `-h` as a shorthand.
</ParamField>

<ParamField query="--no-update-check" type="boolean" default="false">
  Disable the automatic check for new versions on startup.
</ParamField>

### Development Mode
If you are modifying the platform or building new themes, use the development command:

```bash
fair dev
```

<ParamField query="--port" type="integer" default="8000">
  The port for the backend API.
</ParamField>

<ParamField query="--no-frontend" type="boolean" default="false">
  Disable the frontend development server.
</ParamField>

<ParamField query="--no-headless" type="boolean" default="false">
  Serve the bundled frontend from the backend instead of the dev server.
</ParamField>

This command automatically:
1. Starts the **Backend API** (usually on port 8000).
2. Starts the **Frontend Dev Server** (using Bun/Vite).
3. Links them together so changes appear instantly.

## Database Management

FAIR uses migrations to keep your database schema up to date. All database commands are grouped under `fair db`.

### Common Migration Tasks
- **Update to latest:** `fair db upgrade head`
- **Undo last change:** `fair db downgrade -1`
- **Check current version:** `fair db current`
- **View history:** `fair db history`

### Migrating to PostgreSQL
By default, FAIR uses SQLite for simplicity. If you are moving to a production-grade PostgreSQL database, use the migration tool:

```bash
fair db migrate-sqlite-to-postgres --to-postgres "postgresql://user:password@localhost/dbname"
```
*Note: You must run `fair db upgrade head` on your PostgreSQL database first to create the tables before moving the data.*

## Troubleshooting

- **Command not found:** Ensure your Python scripts directory is in your system's PATH.
- **Bun missing:** The `fair dev` command requires [Bun](https://bun.sh) to run the frontend. If you don't have it, use `fair serve` instead.
- **Database errors:** If the platform fails to start after an update, try running `fair db upgrade head`.

## Next Steps
<Columns cols={2}>
    <Card
      title="Courses Guide"
      icon="graduation-cap"
      href="/en/platform/courses"
      arrow="true"
      cta="Learn more"
    >
      Now that your server is running, start organizing your classes.
    </Card>
    
    <Card
      title="Workflows"
      icon="bolt"
      href="/en/platform/workflows"
      arrow="true"
      cta="Learn more"
    >
      Learn how to automate grading using the platform you just started.
    </Card>
</Columns>
