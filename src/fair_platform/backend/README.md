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

### Job/Extension Communications (Current)

As of February 27, 2026, the backend includes:
- `/api/jobs` endpoints (create/state/update/stream)
- `/api/extensions` endpoints (register/list)
- a queue abstraction with local and Redis backends
- a dispatcher service that forwards queued jobs to extension webhooks

Key environment variables:
```bash
FAIR_JOB_QUEUE_BACKEND=local|redis          # default: local
FAIR_REDIS_URL=redis://127.0.0.1:6379/0     # used when backend=redis
FAIR_ENABLE_JOB_DISPATCHER=true|false       # default: true
```

Set `FAIR_ENABLE_JOB_DISPATCHER=false` if you need to disable forwarding jobs to extension webhooks.

Current scalability status:
- Queue:
  - `local` backend is single-process only (not horizontally scalable).
  - `redis` backend supports multi-worker queue sharing and pub/sub updates.
- Dispatcher:
  - Can scale out by running multiple dispatcher instances against Redis queue.
  - Retries exist, but advanced reliability (dead-letter queue, consumer groups, distributed
    locking/claims, durable retry scheduling) is not implemented yet.
- Extension registry:
  - Current implementation is in-memory and process-local.
  - For real multi-instance deployments, registry should move to shared persistent storage.

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
