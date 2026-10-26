# Stable / Nightly verification

Verified on 2026-10-25 against the full canary history, plus main's README change.

- Backend: 73 passing endpoint/auth/access-control/assignment lifecycle checks,
  including default Stable, retired/unknown channel fallback, Nightly defaults,
  and each independent feature kill switch.
- Frontend: 100 passing checks across 36 files in the full run. The remaining
  To-do fixture needed its shared page header isolated (it requires browser
  observers and the app shell); both repaired tests pass in a focused rerun.
  The focused visibility run also passes all 32 other checks.
- TypeScript check and production frontend build pass.
- Chromium loaded the actual production bundle with fixture API responses at
  desktop 1280 px and phone 390 px, for both channels, with no page errors.
- Stable shows Stream, Assignments, Participants; Nightly additionally shows
  Content and Gradebook. Stable does not request notifications or course content.
- Stable direct course-content links redirect to Stream. Component checks cover
  hidden gradebook, learner grades, flow/run/capability URLs, copy selections,
  material filters, and safe behavior before release config is available.

Visibility flags do not change API authorization or remove existing user data.
The same built frontend is used for both runtime channels.
