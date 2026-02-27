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
cd backend
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
DATABASE_URL=postgresql://user:pass@localhost:5432/fair
```
`env.py` normalizes `postgres://` → `postgresql://` and converts relative SQLite paths to an absolute path at project root so all components share the same DB file.

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
FAIR_ENABLE_JOB_DISPATCHER=true|false       # default: false
```

Why `FAIR_ENABLE_JOB_DISPATCHER` defaults to `false`:
- Current registration/auth policy is intentionally minimal (no extension credentials yet).
- Keeping dispatch opt-in avoids accidental job forwarding in environments that have not
  configured extension trust/auth yet.
- This will likely switch to default `true` after extension authentication + authorization
  is added as a stable default path.

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
- If using a PostgreSQL DSN starting with `postgres://`, it is rewritten automatically.
- On Windows, ensure you activate the virtual environment before running commands.
- Enum changes sometimes need manual edits to migration scripts (especially for PostgreSQL).
