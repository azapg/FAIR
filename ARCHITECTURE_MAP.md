# System Architecture Map: Assignments, Artifacts & Submissions

**Visual guide to understand the current state of the codebase**

---

## Backend Architecture Map

### Database Models Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE MODELS                               │
└─────────────────────────────────────────────────────────────────┘

Course                Assignment              Submission
┌────────┐           ┌─────────────┐         ┌──────────────┐
│ id     │───────┐   │ id          │    ┌────│ id           │
│ name   │       │   │ course_id   │◄───┘    │ assignment_id│◄──┐
│ instr..│       └──►│ title       │         │ submitter_id │   │
└────────┘           │ description │         │ submitted_at │   │
                     │ deadline    │         │ status       │   │
                     │ max_grade   │         └──────────────┘   │
                     └─────────────┘                            │
                            │                                    │
                            │                                    │
                     ┌──────┴────────┐                          │
                     │               │                          │
                     ▼               ▼                          │
          ┌──────────────────────────────────┐                 │
          │         Artifact                 │                 │
          ├──────────────────────────────────┤                 │
          │ id                               │                 │
          │ title, type, mime                │                 │
          │ storage_path, storage_type       │                 │
          │ creator_id (FK → users)          │                 │
          │ status, access_level             │                 │
          │ created_at, updated_at           │                 │
          ├──────────────────────────────────┤                 │
          │ DUAL RELATIONSHIPS:              │                 │
          │ - assignment_id (FK)        ────────────────┐      │
          │ - assignments (M2M)         ────────┐       │      │
          │ - submissions (M2M)         ───────────────────────┘
          └──────────────────────────────────┘  │       │
                                                 │       │
          ┌──────────────────────────────────┐  │       │
          │  assignment_artifacts (M2M)      │  │       │
          ├──────────────────────────────────┤  │       │
          │  id (PK)                         │◄─┘       │
          │  assignment_id (FK)              │          │
          │  artifact_id (FK)                │          │
          └──────────────────────────────────┘          │
                                                         │
          ┌──────────────────────────────────┐          │
          │  submission_artifacts (M2M)      │          │
          ├──────────────────────────────────┤          │
          │  id (PK)                         │◄─────────┘
          │  submission_id (FK)              │
          │  artifact_id (FK)                │
          └──────────────────────────────────┘

⚠️  PROBLEM: Artifacts have THREE ways to relate to assignments:
    1. assignment_id FK → Assignment.direct_artifacts
    2. assignment_artifacts M2M → Assignment.artifacts
    3. Implicit via submissions.assignment_id
    These can diverge! No synchronization enforcement.
```

### API Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        API ROUTERS                               │
└─────────────────────────────────────────────────────────────────┘

/api/assignments                    /api/artifacts
┌───────────────────────┐          ┌──────────────────────────┐
│ POST /                │          │ POST /                   │
│ ✅ Multipart form     │          │ ✅ Bulk file upload      │
│ ✅ Files + artifact   │          │ ⚠️  Creates "pending"    │
│    IDs support        │          │ ⚠️  Professor only       │
│ ✅ Atomic transaction │          │                          │
│                       │          │ GET /                    │
│ GET /                 │          │ ✅ Filter support        │
│ ✅ course_id filter   │          │ ✅ Permission checks     │
│ ❌ No artifacts in    │          │                          │
│    response           │          │ GET /{id}                │
│                       │          │ ✅ Permission check      │
│ GET /{id}             │          │                          │
│ ❌ TODO: permissions  │          │ POST /{id}/attach/       │
│ ❌ No artifacts       │          │      assignment/{aid}    │
│                       │          │ ✅ Atomic attach         │
│ PUT /{id}             │          │                          │
│ ❌ TODO: artifact     │          │ POST /{id}/attach/       │
│    updates            │          │      submission/{sid}    │
│                       │          │ ✅ Atomic attach         │
│ DELETE /{id}          │          │                          │
│ ✅ Cascade deletes    │          │ DELETE /{id}/detach/...  │
└───────────────────────┘          │ ⚠️  Manual detach steps  │
                                   └──────────────────────────┘

/api/submissions
┌──────────────────────────────────┐
│ POST /                           │
│ ⚠️  Uses SyntheticSubmission     │
│    schema (not SubmissionCreate!)│
│ ⚠️  Creates synthetic users      │
│ ⚠️  Two-step: upload artifacts   │
│    first, then create submission │
│ ✅ Atomic transaction            │
│                                  │
│ POST /create-with-files          │
│ ✅ Atomic files + submission     │
│ ⚠️  Same synthetic user pattern  │
│ ❌ Frontend doesn't use this!    │
│                                  │
│ GET /                            │
│ ✅ assignment_id filter          │
│ ❌ No permission checks!         │
│ ❌ No nested data (artifacts,    │
│    submitter, assignment)        │
│                                  │
│ GET /{id}                        │
│ ❌ No permission check           │
│ ❌ No nested data                │
│                                  │
│ PUT /{id}                        │
│ ⚠️  TODO: status/timestamp       │
│    updates shouldn't be allowed  │
│ ⚠️  Artifact update does full    │
│    replace (detach all, reattach)│
│                                  │
│ DELETE /{id}                     │
│ ✅ Permission check              │
└──────────────────────────────────┘
```

### Service Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                   ARTIFACT MANAGER SERVICE                       │
│                  (The clean part of the system!)                 │
└─────────────────────────────────────────────────────────────────┘

✅ WELL-DESIGNED:

┌────────────────────────────────────────┐
│  Core CRUD Operations                  │
├────────────────────────────────────────┤
│  - create_artifact()                   │
│  - get_artifact()                      │
│  - list_artifacts()                    │
│  - update_artifact()                   │
│  - delete_artifact()                   │
│                                        │
│  All with permission checks!           │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Atomic Operations                     │
├────────────────────────────────────────┤
│  - create_artifacts_bulk()             │
│  - attach_to_assignment()              │
│  - attach_to_submission()              │
│  - detach_from_assignment()            │
│  - detach_from_submission()            │
│                                        │
│  Handles status transitions & orphans  │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Lifecycle Management                  │
├────────────────────────────────────────┤
│  - mark_orphaned()                     │
│  - cleanup_orphaned()                  │
│                                        │
│  Admin cleanup for abandoned artifacts │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Permission System                     │
├────────────────────────────────────────┤
│  - can_view()                          │
│  - can_edit()                          │
│  - can_delete()                        │
│                                        │
│  Role-based + ownership checks         │
└────────────────────────────────────────┘

⚠️  TODOs:
    - Enrollment system integration
    - Junction table sync concerns
```

---

## Frontend Architecture Map

### Type Definitions (The Mess)

```
┌─────────────────────────────────────────────────────────────────┐
│                      TYPE DEFINITIONS                            │
│                   (Three sources of truth!)                      │
└─────────────────────────────────────────────────────────────────┘

Assignment Types - Location A (use-assignments.ts)
┌──────────────────────────────────────┐
│ id: string                           │
│ course_id: string                    │
│ title: string                        │
│ description?: string | null          │
│ deadline: string | null      ← snake_case
│ max_grade?: Grade | null     ← snake_case
└──────────────────────────────────────┘

Assignment Types - Location B (demo.tsx)
┌──────────────────────────────────────┐
│ id: string                           │
│ title: string                        │
│ description: string                  │
│ dueDate: Date               ← camelCase!
│ maxGrade: number            ← Different type!
└──────────────────────────────────────┘

Assignment Types - Location C (assignments.tsx)
┌──────────────────────────────────────┐
│ id: string                           │
│ title: string                        │
│ description?: string                 │
│ dueDate?: Date              ← camelCase!
│ totalPoints?: Grade         ← Different name!
│ createdAt: Date             ← Not in backend!
│ updatedAt: Date             ← Not in backend!
└──────────────────────────────────────┘

❌ PROBLEM: Three incompatible definitions!
   No single source of truth!

Artifact Types - Location A (use-artifacts.ts)
┌──────────────────────────────────────┐
│ id: string                           │
│ title: string                        │
│ storagePath: string      ← camelCase │
│ storageType: string      ← camelCase │
│ creatorId: string        ← camelCase │
│ createdAt: string        ← camelCase │
│ status: string                       │
│ courseId?: string        ← camelCase │
│ assignmentId?: string    ← camelCase │
│ accessLevel: string      ← camelCase │
└──────────────────────────────────────┘

Artifact Types - Location B (assignments.tsx - ArtifactChip)
┌──────────────────────────────────────┐
│ id: string                           │
│ title: string                        │
│ mime: string                         │
│ artifact_type: string    ← snake_case!
│ storage_type: string     ← snake_case!
│ storage_path: string     ← snake_case!
│ fileName: string         ← Not in backend!
│ status: "pending" | "uploading" |    │
│         "uploaded" | "error"         │
│         ← Client upload states!      │
└──────────────────────────────────────┘

⚠️  PROBLEM: Two different purposes
    (API vs upload tracking)

Submission Types - submissions.tsx
┌──────────────────────────────────────┐
│ id: string                           │
│ name: string             ← Not in backend!
│ status: SubmissionStatus             │
│ grade?: number           ← Not in backend!
│ feedback?: string        ← Not in backend!
│ submittedAt?: Date                   │
└──────────────────────────────────────┘

❌ MISSING:
   - assignment_id
   - submitter_id
   - official_run_id

⚠️  Should be:
   - name → fetch from submitter relationship
   - grade → fetch from workflow results
   - feedback → fetch from workflow results
```

### API Hooks Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                         API HOOKS                                │
└─────────────────────────────────────────────────────────────────┘

use-assignments.ts                use-artifacts.ts
┌───────────────────────┐        ┌──────────────────────────┐
│ ✅ useAssignments()   │        │ ✅ useArtifacts()        │
│ ⚠️  useAssignment()   │        │ ✅ useArtifact()         │
│    (used but not      │        │ ⚠️  useCreateArtifact()  │
│     defined here!)    │        │    (unused, wrong API)   │
│ ✅ useCreateAssignment│        │ ✅ useUpdateArtifact()   │
│ ✅ useUpdateAssignment│        │ ✅ useDeleteArtifact()   │
│ ✅ useDeleteAssignment│        │                          │
│                       │        │ ❌ No attach/detach hooks│
│ ✅ FormData handling  │        └──────────────────────────┘
│ ✅ File upload support│
└───────────────────────┘        

use-submissions.ts
┌────────────────────────────────┐
│ ❌ FILE DOES NOT EXIST!        │
│                                │
│ MISSING:                       │
│ - useSubmissions()             │
│ - useSubmission()              │
│ - useCreateSubmission()        │
│ - useUpdateSubmission()        │
│ - useDeleteSubmission()        │
│                                │
│ Frontend uses direct api.post()│
│ No query cache integration!    │
└────────────────────────────────┘
```

### Component Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPONENT HIERARCHY                          │
└─────────────────────────────────────────────────────────────────┘

AssignmentPage
├── useAssignment(assignmentId)        ✅ Fetches assignment
├── useCourse(assignment.course_id)    ⚠️  Chained query
├── useArtifacts({assignmentId})       ✅ Fetches artifacts
└── useSubmissions(assignmentId)       ❌ MISSING!
    │
    ├── Renders Assignment Details
    ├── Displays Artifacts
    │
    └── SubmissionsTable
        ├── data={[]}                   ❌ HARDCODED EMPTY!
        └── columns                     ✅ Column definitions

CreateSubmissionDialog
├── State:
│   ├── username: string
│   ├── files: FileList | null
│   └── open: boolean
│
├── handleCreate():                    ⚠️  TWO-STEP PROCESS
│   ├── IF files:
│   │   ├── POST /api/artifacts       Step 1: Upload files
│   │   └── POST /api/submissions     Step 2: Create submission
│   └── ELSE:
│       └── POST /api/submissions     Direct submission
│
└── ❌ No query invalidation after success!

⚠️  PROBLEMS:
    - Two-step not atomic (can fail between steps)
    - No error handling
    - No loading states
    - No success feedback
    - Submissions don't refresh
```

---

## Data Flow Diagrams

### Current Flow: Create Submission (BROKEN)

```
User Action                  Frontend                    Backend
────────────────────────────────────────────────────────────────────

1. Click "Add"
   Enter name, files
   Click "Create"
                    ┌──────────────────────┐
                    │ CreateSubmissionDialog│
                    └──────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ IF files selected? │
                    └─────────┬─────────┘
                              │ YES
                    ┌─────────▼─────────────┐
                    │ api.post("/artifacts")│
                    │ FormData with files   │
                    └─────────┬─────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ artifacts/router.py    │
                    │ create_artifact()      │
                    │ ArtifactManager        │
                    │ status = "pending"     │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼─────────────┐
                    │ Returns artifact IDs  │
                    └─────────┬─────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ api.post("/submissions")│
                    │ {assignment_id,        │
                    │  submitter: name,      │
                    │  artifact_ids: [...]}  │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ submissions/router.py  │
                    │ create_submission()    │
                    │ Create synthetic user  │
                    │ Create submission      │
                    │ attach_to_submission() │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼─────────────┐
                    │ Database updated      │
                    └─────────┬─────────────┘
                              │
                    ┌─────────▼─────────────┐
                    │ Dialog closes         │
                    │ ❌ NO QUERY INVALIDATE│
                    └───────────────────────┘
                              
User sees nothing changed!    ❌ TABLE STILL SHOWS []

⚠️  FAILURE POINTS:
    1. If artifact upload fails → user sees error in console only
    2. If submission creation fails → orphaned artifacts
    3. No query invalidation → UI doesn't update
    4. Submissions are never fetched anyway!
```

### Fixed Flow: Create Submission (WORKING)

```
User Action                  Frontend                    Backend
────────────────────────────────────────────────────────────────────

1. Click "Add"
   Enter name, files
   Click "Create"
                    ┌──────────────────────┐
                    │ CreateSubmissionDialog│
                    │ useCreateSubmission() │
                    └──────────────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ IF files selected?     │
                    └─────────┬──────────────┘
                              │ YES
                    ┌─────────▼──────────────┐
                    │ api.post("/artifacts") │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ createSubmission.      │
                    │   mutateAsync({...})   │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ submissions/router.py  │
                    │ (same backend logic)   │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ onSuccess() callback   │
                    │ queryClient.invalidate│
                    │   Queries(['submissions│
                    │   ', assignmentId])    │
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ useSubmissions() refetch│
                    └─────────┬──────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ SubmissionsTable       │
                    │ data={submissions}     │
                    │ ✅ UPDATES AUTOMATICALLY│
                    └────────────────────────┘

User sees new submission!     ✅ TABLE UPDATES

✅ IMPROVEMENTS:
   1. Query invalidation triggers refetch
   2. TanStack Query caching
   3. Loading states handled
   4. Error handling via mutation state
```

### Ideal Flow: Create Submission (FUTURE)

```
User Action                  Frontend                    Backend
────────────────────────────────────────────────────────────────────

1. Click "Add"
   Enter name, files
   Click "Create"
                    ┌──────────────────────┐
                    │ CreateSubmissionDialog│
                    │ useCreateSubmission() │
                    └──────────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ createSubmissionWithFiles  │
                    │   .mutateAsync({           │
                    │     assignmentId,          │
                    │     submitter: name,       │
                    │     files: [...]           │
                    │   })                       │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ POST /api/submissions/     │
                    │      create-with-files     │
                    │ (ATOMIC ENDPOINT)          │
                    │                            │
                    │ Single FormData:           │
                    │ - assignment_id            │
                    │ - submitter_name           │
                    │ - files[]                  │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ submissions/router.py      │
                    │ BEGIN TRANSACTION          │
                    │ ├─ Create synthetic user   │
                    │ ├─ Create submission       │
                    │ ├─ Upload artifacts        │
                    │ └─ Link artifacts          │
                    │ COMMIT TRANSACTION         │
                    │                            │
                    │ IF ANY STEP FAILS:         │
                    │ └─ ROLLBACK ALL            │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ Return full submission     │
                    │ with nested artifacts      │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ onSuccess() invalidates    │
                    │ useSubmissions() refetches │
                    │ ✅ ONE ATOMIC OPERATION    │
                    │ ✅ AUTO ROLLBACK ON ERROR  │
                    │ ✅ NESTED DATA RETURNED    │
                    └────────────────────────────┘

✅ BENEFITS:
   1. Single API call (not two-step)
   2. Atomic transaction (rollback on failure)
   3. No orphaned artifacts possible
   4. Simpler frontend code
   5. Better error handling
```

---

## Permission System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     PERMISSION MATRIX                            │
└─────────────────────────────────────────────────────────────────┘

Artifact Permissions (via ArtifactManager.can_view/edit/delete):

Role      │ View Own │ View Course │ View Others │ Edit │ Delete
──────────┼──────────┼─────────────┼─────────────┼──────┼────────
Admin     │    ✅    │     ✅      │     ✅      │  ✅  │   ✅
Professor │    ✅    │     ✅      │     ❌      │  ✅* │   ✅*
Student   │    ✅    │     ⚠️      │     ❌      │  ⚠️  │   ⚠️

* If course instructor
⚠️ Depends on access_level and enrollment (not fully implemented)

Assignment Permissions:

Action           │ Admin │ Professor │ Student
─────────────────┼───────┼───────────┼─────────
Create           │  ✅   │    ✅*    │   ❌
List by course   │  ✅   │    ✅*    │   ⚠️
Get single       │  ✅   │    ⚠️     │   ⚠️
Update           │  ✅   │    ✅*    │   ❌
Delete           │  ✅   │    ✅*    │   ❌

* If course instructor
⚠️ TODO: enrollment checks

Submission Permissions:

Action           │ Admin │ Professor │ Student │ Owner
─────────────────┼───────┼───────────┼─────────┼───────
Create synthetic │  ✅   │    ✅     │   ❌    │  N/A
List all         │  ❌ NO PERMISSION CHECK!   │  ❌
Get single       │  ❌ NO PERMISSION CHECK!   │  ❌
Update           │  ✅   │    ❌     │   ❌    │  ✅
Delete           │  ✅   │    ❌     │   ❌    │  ✅

⚠️  CRITICAL SECURITY ISSUES:
    - Anyone can list submissions
    - Anyone can view submission details
    - No enrollment validation
```

---

## Storage & File Handling

```
┌─────────────────────────────────────────────────────────────────┐
│                    FILE STORAGE FLOW                             │
└─────────────────────────────────────────────────────────────────┘

Frontend Upload             ArtifactManager              Storage
──────────────────────────────────────────────────────────────────

FormData                    create_artifact()
  ├─ file: UploadFile            │
  ├─ creator: User               │
  └─ metadata                    │
         │                       │
         └──────────────────────>│
                                 │
                       ┌─────────▼────────┐
                       │ Generate UUID    │
                       │ artifact_id      │
                       └─────────┬────────┘
                                 │
                       ┌─────────▼─────────┐
                       │ _store_file()     │
                       │ storage.save()    │
                       └─────────┬─────────┘
                                 │
                                 │        ┌──────────────┐
                                 │────────│ Local storage│
                                 │        │ /data/       │
                                 │        │ artifacts/   │
                                 │        │ {uuid}/      │
                                 │        │ {filename}   │
                                 │        └──────────────┘
                                 │
                       ┌─────────▼─────────┐
                       │ Create DB record  │
                       │ Artifact(         │
                       │   storage_path,   │
                       │   creator_id,     │
                       │   status=pending  │
                       │ )                 │
                       └─────────┬─────────┘
                                 │
                       ┌─────────▼─────────┐
                       │ db.add()          │
                       │ db.flush()        │
                       └─────────┬─────────┘
                                 │
                 IF ERROR ───────┤
                 │               │
       ┌─────────▼─────┐         │
       │ _delete_file()│         │
       │ Cleanup!      │         │
       └───────────────┘         │
                                 │
                       ┌─────────▼─────────┐
                       │ Return Artifact   │
                       └───────────────────┘

✅ WELL-DESIGNED:
   - Automatic cleanup on failure
   - UUID-based storage paths (no collisions)
   - Transaction-safe (rollback cleans files)
```

---

## Key Takeaways

### What's Clean ✅

1. **ArtifactManager Service** - Centralized, well-architected
2. **Permission System** - Role-based checks implemented
3. **Lifecycle Management** - Status tracking, orphan handling
4. **Atomic Operations** - Transaction safety in place
5. **File Storage** - Error-safe with cleanup

### What's Broken ❌

1. **No Submission Fetching** - Frontend never requests submissions
2. **No Query Invalidation** - Create submission doesn't trigger refetch
3. **Type Mismatches** - Frontend/backend field names don't match
4. **Missing Permission Checks** - Submission list/get have no auth
5. **Three Assignment Types** - No single source of truth

### What's Ugly ⚠️

1. **Dual Artifact Relationships** - Assignment has both FK and M2M
2. **Synthetic Users** - Creates fake users in main user table
3. **Two-Step Uploads** - Not atomic, can leave orphans
4. **Schema Typo** - `artifacts_ids` instead of `artifact_ids`
5. **No Nested Data** - API doesn't return relationships

### Priority Order

**Fix Now** (30 minutes):
- Create `use-submissions.ts`
- Update `CreateSubmissionDialog`
- Update `AssignmentPage`

**Fix Soon** (2-4 hours):
- Add permission checks to submission endpoints
- Fix type inconsistencies
- Add error handling and toast notifications

**Fix Later** (post-MVP):
- Refactor synthetic user system
- Switch to atomic submission endpoint
- Consolidate artifact relationships
- Add nested API responses
- Generate types from OpenAPI spec

---

## Questions to Answer Before Refactoring

1. **Artifact Relationships**: Pick one pattern (FK or M2M or both)?
2. **Synthetic Users**: Separate table or flag in users table?
3. **Type Generation**: Manual or OpenAPI/Prisma schema-driven?
4. **Nested Data**: Eager load or separate queries?
5. **Enrollment System**: When to implement, blocks what features?
6. **Grade Storage**: In submission or separate grades table?
7. **File Uploads**: Keep two-step or enforce atomic endpoint?

**Recommendation**: Ship MVP first, answer these during refactor sprint! 🚀
