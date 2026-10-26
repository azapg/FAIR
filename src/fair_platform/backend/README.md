# Backend

## Structure
```
backend/
  alembic.ini            # Alembic config (fallback URL, logging)
  alembic/
    env.py               # Loads DATABASE_URL / sqlite fallback, imports models
    versions/            # Migration scripts
  data/
    database.py          # get_database_url(), Base, engine
    models/              # SQLAlchemy models (imported for autogenerate)
```

## Usage
From project root or backend directory:

```bash
# (Recommended) Create & activate a virtual environment first
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1

# Install project (root already depends on alembic + sqlalchemy)
pip install -e .

# Run existing migrations (creates fair.db if missing)
alembic upgrade head

# Create a new migration after editing/adding models
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# Downgrade (example)
alembic downgrade -1
```

## Configuration
Environment variable `DATABASE_URL` (optionally via a `.env` file) overrides the default `sqlite:///fair.db`.

Examples:
```
DATABASE_URL=sqlite:///fair.db
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/fair
```
`env.py` normalizes `postgres://`/`postgresql://` → `postgresql+psycopg://` and converts relative SQLite paths to an absolute path at project root so all components share the same DB file.

Set `FAIR_AUTO_MIGRATE=0` to disable startup auto-migration (`upgrade head` runs automatically by default).
If you disable auto-migrate and still want local/test schema bootstrap from ORM metadata, set `FAIR_ALLOW_CREATE_ALL=1` explicitly.
If both are disabled, startup proceeds with a warning and no schema bootstrap (runtime DB errors are likely until migrations are applied).

## Database Contract
- Primary supported production database: PostgreSQL (target version 18).
- SQLite remains supported for lightweight local/testing scenarios.
- JSON document fields must use SQLAlchemy JSON with PostgreSQL JSONB variant.
- Schema changes must be applied through Alembic migrations; avoid relying on runtime `create_all` for production schema evolution.

## LMS deployment profiles

- Researcher/local: SQLite (`DATABASE_URL=sqlite:///fair.db`) and `FAIR_STORAGE_BACKEND=local`.
- Institution: PostgreSQL and `FAIR_STORAGE_BACKEND=s3` with `S3_BUCKET_NAME` plus provider credentials/endpoint as needed.
- `FAIR_STORAGE_BACKENDS=local,s3` supports a staged storage migration while selecting the write backend with `FAIR_STORAGE_BACKEND`.

See `docs/en/platform/lms-mvp.md` and the root `.env.example` for the complete MVP operations contract. The institutional target remains a modular monolith with durable external state; microservices and extreme-scale optimization are not required for this MVP.

### Execution/Extension communications

The FAIR 1.0 boundary lives under `/api/v1`:

- clients create and observe Executions rather than queue records;
- Extension installations declare versioned capabilities and dispatch URLs;
- contextual grants authorize declared effects;
- a transactional database outbox leases and sends idempotent commands directly to enabled installations;
- Extensions authenticate scoped event and Artifact calls back to FAIR;
- ordered Execution Events are the durable progress and result record.

Public Job, Plugin, and unversioned Extension routes have been removed. Outbox rows, leases, retries, and dead-letter state are internal delivery details.

Platform-to-Extension request signing and delegated tokens remain contract-hardening work. Until signed dispatch is available, protect Extension dispatch endpoints with trusted transport and network controls.

## Adding Models
1. Create model in `backend/data/models/`
2. Import it in `backend/data/models/__init__.py`
3. Run `alembic revision --autogenerate -m "add <model>"`
4. Review generated script (check types, constraints)
5. Apply with `alembic upgrade head`

## Troubleshooting
- If Alembic cannot find models, ensure `backend` root is on `PYTHONPATH` (handled automatically in `env.py`).
- If using a PostgreSQL DSN starting with `postgres://` or `postgresql://`, it is rewritten automatically to `postgresql+psycopg://`.
- On Windows, ensure you activate the virtual environment before running commands.
- Enum changes sometimes need manual edits to migration scripts (especially for PostgreSQL).
