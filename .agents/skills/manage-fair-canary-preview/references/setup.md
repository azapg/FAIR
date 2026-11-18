# FAIR canary preview reference

## Architecture

Traffic follows this path:

`Tailnet client -> native Windows Tailscale Serve :8443 -> Windows localhost:3811 -> WSL FAIR origin`

Get the canonical tailnet URL with `fair-canary url`.

The native Windows node also has an unrelated HTTPS port 443 route to `http://127.0.0.1:3774`. Preserve it.

## WSL components

- Managed worktree: `~/worktrees/FAIR/canary`
- Origin: `http://127.0.0.1:3811`
- CLI helper: `~/.local/bin/fair-canary`
- Server launcher: `~/.local/bin/fair-canary-server`
- App unit: `~/.config/systemd/user/fair-canary.service`
- Refresh unit/timer: `fair-canary-refresh.service` and `fair-canary-refresh.timer`
- Database: `~/.local/share/fair-canary/fair.db`
- Secret: `~/.local/state/fair-canary/secret-key`; never print it
- Disabled fallback daemon: `tailscaled-fair.service`

The server launcher sets an isolated SQLite database and XDG directories, performs migrations, enables the execution dispatcher, disables update checks, uses secure session cookies, and sets both FAIR public URLs to the canonical HTTPS URL.

## Routine commands

```bash
fair-canary status
fair-canary start
fair-canary stop
fair-canary restart
fair-canary update
fair-canary url
fair-canary logs
```

The hourly refresh timer fetches `origin/nightly`, fast-forwards only, rebuilds when the branch advances, refuses a dirty managed worktree, and restarts after a clean build when Nightly is selected.

## Native Windows publisher

Read-only checks in Windows PowerShell:

```powershell
curl.exe http://localhost:3811/health
& "$env:ProgramFiles\Tailscale\tailscale.exe" serve status
```

Expected routes include the existing 443 route and FAIR on 8443. Restore only FAIR with:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" serve --https=8443 --bg http://localhost:3811
```

Do not issue a root/default `tailscale serve` command that could replace the port 443 route.

## Troubleshooting sequence

1. Run the bundled diagnostic script.
2. If local health fails, inspect `fair-canary logs`; migrations can make startup take several seconds.
3. If local health passes but the native URL returns 502, retry for ten seconds. Windows localhost forwarding reconnects after WSL listener restarts.
4. If 502 persists, ask the user to run the two PowerShell checks above.
5. If assets remain pending, compare document versus JS/CSS completion and inspect response compression. Canary includes gzip middleware from PR #235; the main JS should return `Content-Encoding: gzip` when requested with `Accept-Encoding: gzip`.
6. Keep the nested WSL Tailscale daemon disabled. It ran unprivileged userspace networking with undersized UDP buffers and previously stalled large transfers.

## Security and source changes

- The native URL is tailnet-only.
- Keep secure cookies enabled for HTTPS.
- Preview deployments use the shared canary database by default so the user's existing account, courses, and test data remain available. Do not create `.fair-preview.env` or switch to an isolated database unless the user explicitly authorizes data isolation.
- If a worktree's migrations cannot run against the shared database, stop and ask the user; migration incompatibility is not permission to create a separate database.
- Do not expose the app through Funnel, a public quick tunnel, or a public bind without explicit user authorization.
- Do not edit source in the managed canary worktree. Use a separate worktree and a PR to `nightly`, then deploy with `fair-canary update`.
