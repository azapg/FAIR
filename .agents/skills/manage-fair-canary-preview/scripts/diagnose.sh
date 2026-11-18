#!/usr/bin/env bash
set -u

readonly worktree="$HOME/worktrees/FAIR/canary"
readonly local_url="http://127.0.0.1:3811"

printf 'app=%s\n' "$(systemctl --user is-active fair-canary.service 2>/dev/null || true)"
printf 'app_enabled=%s\n' "$(systemctl --user is-enabled fair-canary.service 2>/dev/null || true)"
printf 'refresh_timer=%s\n' "$(systemctl --user is-active fair-canary-refresh.timer 2>/dev/null || true)"
printf 'refresh_enabled=%s\n' "$(systemctl --user is-enabled fair-canary-refresh.timer 2>/dev/null || true)"
printf 'nested_tailscale=%s\n' "$(systemctl --user is-active tailscaled-fair.service 2>/dev/null || true)"
printf 'nested_tailscale_enabled=%s\n' "$(systemctl --user is-enabled tailscaled-fair.service 2>/dev/null || true)"

if health_metrics="$(curl --max-time 5 -fsS -o /dev/null \
  -w 'code=%{http_code} total=%{time_total}s' "${local_url}/health" 2>/dev/null)"; then
  printf 'origin_health=%s\n' "${health_metrics}"
else
  echo 'origin_health=unavailable'
fi

printf 'revision=%s\n' "$(git -C "${worktree}" rev-parse --short HEAD 2>/dev/null || true)"
printf 'branch=%s\n' "$(git -C "${worktree}" branch --show-current 2>/dev/null || true)"
if [[ -z "$(git -C "${worktree}" status --short 2>/dev/null)" ]]; then
  echo 'worktree=clean'
else
  echo 'worktree=dirty'
fi
printf 'public_url=%s\n' "$(fair-canary url 2>/dev/null || printf 'unavailable')"
