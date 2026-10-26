# Stable and Nightly

`main` is Stable. `nightly` is the development branch and replaces `canary`.
Merge feature branches into `nightly`, then promote tested changes to `main`
with a merge commit so both branches keep their shared history.

Deploy the same code with `FAIR_RELEASE_CHANNEL=stable` (the default) or
`FAIR_RELEASE_CHANNEL=nightly`. Unknown channel names fall back to Stable.
The runtime `/api/v1/system/config` endpoint supplies the channel and flags;
frontend builds are identical for both channels. Restart/redeploy after changing
variables. No database or user data is removed when a feature is hidden.

| Feature | Stable | Nightly | Nightly kill switch |
| --- | --- | --- | --- |
| To-do | Hidden | Visible | `FAIR_FEATURE_TODO=false` |
| Inbox | Hidden | Visible | `FAIR_FEATURE_INBOX=false` |
| Extensions management | Hidden | Visible | `FAIR_FEATURE_EXTENSIONS=false` |
| Course content | Hidden | Visible | `FAIR_FEATURE_COURSE_CONTENT=false` |
| Gradebook and course grade summaries | Hidden | Visible | `FAIR_FEATURE_GRADEBOOK=false` |

Stable ignores experimental opt-ins. Promote a proven feature by changing its
release default in code, with verification of its navigation and direct links.
Flags control UI visibility; existing API permissions and internal grading and
extension execution still apply in both channels.

The learner Dashboard requires To-do, course content, and gradebook, so it is
hidden unless all three are enabled. Course-copy requests exclude hidden content,
quizzes, gradebook structure, and extension flows. Course settings keep internal
artifacts available, while extension management (flows, runs, capabilities) follows
the Extensions flag. Assignment grading, returned feedback, courses, rubrics,
Stream announcements, participants, and files remain available on Stable.

## Hosted channels

- Railway `production`: source branch `main`, `FAIR_RELEASE_CHANNEL=stable`.
- Railway `staging`: source branch `nightly`, `FAIR_RELEASE_CHANNEL=nightly`.
- Each environment keeps its own existing data volume and secrets.

The Railway template and infrastructure defaults target Stable. CI checks pushes
and pull requests for `main` and `nightly`.

## Allan's phone preview

The persistent phone preview follows `nightly` with
`FAIR_RELEASE_CHANNEL=nightly`. Its URL remains
`https://alam.tailf325ec.ts.net:8443`. Use `fair-nightly status`,
`fair-nightly update`, and `fair-nightly use nightly`.
Existing service names and data paths retain their legacy names for compatibility;
the database, secret key, active development previews, and Windows publishing
routes are preserved.
