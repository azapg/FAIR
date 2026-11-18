---
name: manage-fair-canary-preview
description: Operate and troubleshoot Allan's always-on FAIR canary preview in WSL, including status, logs, restarts, canary updates/builds, native Windows Tailscale Serve publishing, HTTPS/session configuration, and recovery from 502 or unreachable states. Use when asked about the FAIR phone preview, FAIR canary dev server, remote FAIR testing URL, port 3811, Tailscale port 8443, or the `fair-canary` helper.
---

# Manage FAIR Canary Preview

Manage the machine-specific FAIR canary preview without disturbing other Tailscale routes or repository work.

## Start with evidence

1. Read [references/setup.md](references/setup.md) completely before changing configuration.
2. Run `scripts/diagnose.sh` for a read-only snapshot.
3. Distinguish origin failures from publisher failures:
   - Origin unhealthy: inspect `fair-canary logs` and the systemd unit.
   - Origin healthy but remote unavailable: inspect native Windows Tailscale Serve from PowerShell.
   - A 502 immediately after restart: wait up to ten seconds and retry before diagnosing further.

## Perform common operations

- Check: run `fair-canary status` and `scripts/diagnose.sh`.
- Restart: run `fair-canary restart`, then confirm local health.
- Update: run `fair-canary update`. Respect its dirty-worktree guard and do not discard user changes.
- Follow logs: run `fair-canary logs`.
- Print the canonical URL: run `fair-canary url`.

Use `fair-canary update` for updates. It fetches `origin/nightly`, fast-forwards, builds, checks the tracked worktree, and waits for health after a restart.

## Preview in-progress work without merging to canary

The Tailscale URL always points at port 3811, which serves whichever worktree is the *active preview target* (recorded in `~/.local/state/fair-canary/active-target`). One slot exists; switching is instant and reversible.

- Point the phone preview at any FAIR worktree (dirty trees allowed): `fair-canary deploy <path>`. It builds the worktree if needed (`./build.sh`), never touches the canary worktree, restarts the service, waits for health, and prints the usual URL.
- Restore the Nightly preview with `fair-canary use nightly`.
- Confirm the selected preview with `fair-canary status`. It reports `nightly (<rev>)` or `DEV <path> (<rev>)`.

Database sharing:

- By default a deployed worktree uses the shared canary database and secret key, so preview data matches canary.
- Treat the shared canary database as the user's default and preserve it unless the user explicitly asks for an isolated database. Never infer permission to isolate from a migration error, a test account, or a request to preview a worktree.
- Never create or add `<worktree>/.fair-preview.env` automatically. It overrides the shared database and can make the user's existing courses, account, and test data appear to disappear.
- If deploy fails health with an alembic "Can't locate revision" error, stop, report that the branch's migrations are incompatible with the shared DB, and ask for explicit approval before creating an isolated database. Keep the active preview on the prior target until the user decides.
- Only after explicit approval to isolate may `<worktree>/.fair-preview.env` be created with `KEY=value` lines. Use an absolute database path under `~/.local/share/fair-canary/preview-dbs/`.

## Preserve the publishing architecture

- Keep FAIR on native Windows Tailscale Serve HTTPS port 8443.
- Preserve the existing Windows HTTPS port 443 route to local port 3774.
- Keep the nested WSL `tailscaled-fair.service` disabled; it previously stalled static asset transfers.
- Keep `FAIR_SESSION_COOKIE_SECURE=1` and the canonical HTTPS URL aligned.
- Do not make the preview public with Funnel or an unauthenticated tunnel without explicit authorization.

If Windows Serve needs restoration, ask the user to run the exact PowerShell command in the reference. Verify existing Serve routes first and never replace the port 443 mapping.

## Change FAIR source safely

Do not develop directly in the managed canary worktree. Create an isolated branch or worktree and test it with `fair-canary deploy <path>`. For an authorized rollout to Nightly, open a PR against `nightly` and merge when appropriate. Run `fair-canary update` followed by `fair-canary use nightly` to refresh and select the Nightly preview.

When a dev preview is active, `fair-canary update` still refreshes and builds the canary worktree but deliberately does not restart the service — the dev preview keeps running.

## Completion checks

Confirm all of the following before reporting success:

- `fair-canary.service` is active and enabled.
- Local `/health` returns 200.
- The managed canary worktree is clean and matches `origin/nightly` after an update.
- `fair-canary-refresh.timer` is active and enabled.
- The canonical URL reported by `fair-canary url` remains the same unless the user deliberately changes the architecture.
- Remote validation is performed from a tailnet device when publisher behavior changed.
