# LMS MVP operations

FAIR is LMS-complete at an MVP level when a teacher and a student can complete the ordinary class loop without enabling an AI workflow, plugin, or extension.

## Included MVP loop

- Create, organize, archive, and reopen courses.
- Maintain an active roster with owner, assistant, and student course roles.
- Publish announcements and class materials; allow class comments.
- Draft, publish, close, and unpublish assignments.
- Let enrolled students submit their own work, including numbered attempts and late state.
- Give students a cross-course to-do view for missing and submitted work.
- Show course staff a roster-derived grading queue and gradebook, including missing work.
- Keep draft grades private, then return a score and feedback to the student.
- Keep submission comment threads private to the owning student and course staff.
- Notify students about published assignments and class posts, and notify authors about comments.

This MVP deliberately does not include quizzes, standards/outcomes, attendance, SIS/LTI integrations, advanced analytics, group assignments, peer review, calendars, microservices, or multi-region scaling. AI graders and learning agents can integrate with this foundation but are not required for LMS behavior.

## Researcher/local profile

Use one process, SQLite, and local files. This is the default and is intended for individual researchers, reproducible studies, demos, and development.

```env
FAIR_DEPLOYMENT_MODE=COMMUNITY
DATABASE_URL=sqlite:///fair.db
FAIR_STORAGE_BACKEND=local
FAIR_AUTO_MIGRATE=1
SECRET_KEY=replace-for-shared-environments
```

SQLite foreign keys are enabled by the runtime. Uploaded files remain below FAIR's application data directory and downloads are served through artifact authorization; there is no public raw-file route.

Back up both the SQLite database and the uploads directory together. This profile is single-node and should not be treated as shared institutional infrastructure.

## Institutional profile

Use PostgreSQL and an S3-compatible object store. This keeps the same modular-monolith application and API while moving durable state to services suitable for an institution.

```env
FAIR_DEPLOYMENT_MODE=ENTERPRISE
DATABASE_URL=postgresql+psycopg://fair:replace-me@postgres:5432/fair
FAIR_STORAGE_BACKEND=s3
S3_BUCKET_NAME=fair-institution
S3_REGION=us-east-1
S3_ENDPOINT_URL=https://s3.example.edu
S3_ACCESS_KEY=replace-me
S3_SECRET_KEY=replace-me
SECRET_KEY=replace-with-a-long-random-secret
FAIR_CORS_ORIGINS=https://fair.example.edu
FAIR_AUTO_MIGRATE=1
```

`S3_ENDPOINT_URL` is optional for AWS S3 and required for many S3-compatible providers. Prefer workload or instance credentials where available instead of static access keys. Enterprise mode refuses the built-in development secret.

The MVP scalability target is a well-operated modular monolith backed by PostgreSQL and object storage. Run database migrations before or during a controlled deployment, use ordinary database/object-store backups, and add application replicas only after externalizing any process-local queues needed by the enabled extension features. Microservices, sharding, and million-user optimization are explicitly outside the MVP.

## Migration and verification

Startup applies Alembic migrations by default. Operators can instead run:

```bash
uv run alembic upgrade head
```

The repository rehearses the complete migration chain on SQLite and provides opt-in PostgreSQL integration tests through `POSTGRES_TEST_URL`. Storage contract tests cover local-file round trips/path safety and the S3 upload, read, delete, and signed-download interface. Set `S3_TEST_ENDPOINT` (plus optional `S3_TEST_ACCESS_KEY`, `S3_TEST_SECRET_KEY`, and `S3_TEST_REGION`) to run the same round trip against an actual S3-compatible service. Frontend component interaction tests run with `cd frontend-dev && bun run test`; `bun run build` remains the production bundle gate.

For a staged local-to-S3 move, configure both schemes so old `local://` artifacts remain readable while new writes use S3:

```env
FAIR_STORAGE_BACKENDS=local,s3
FAIR_STORAGE_BACKEND=s3
```

Moving existing object bytes is an operator migration step; changing the default backend alone does not copy existing files.
