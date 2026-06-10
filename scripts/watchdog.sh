#!/usr/bin/env bash
# Daily watchdog: verifies that today's pool post actually went out, and raises a
# GitHub issue (which GitHub emails to the repo owner) if it did not.
#
# "Went out" = at least one SUCCESSFUL run of telegram-scheduler.yml created today (UTC),
# whether from the daily cron or a manual dispatch.
#
# Env (provided by the workflow):
#   GH_TOKEN            - token with actions:read + issues:write (github.token)
#   GITHUB_REPOSITORY   - owner/repo (set automatically by Actions)
# Test hooks:
#   WATCHDOG_DATE_OVERRIDE=YYYY-MM-DD   - check a specific day instead of today
#   WATCHDOG_DRYRUN=1                   - print the alert instead of creating an issue
set -euo pipefail
: "${GITHUB_REPOSITORY:?}"
: "${GH_TOKEN:?}"

API="https://api.github.com/repos/${GITHUB_REPOSITORY}"
TODAY="${WATCHDOG_DATE_OVERRIDE:-$(date -u +%F)}"
AUTH=(-H "Authorization: token ${GH_TOKEN}")

runs_json="$(curl -fsS "${AUTH[@]}" \
  "${API}/actions/workflows/telegram-scheduler.yml/runs?per_page=40")"

read -r OK FAILED < <(printf '%s' "$runs_json" | python3 -c '
import sys, json
day = sys.argv[1]
data = json.load(sys.stdin).get("workflow_runs", [])
ok     = sum(1 for r in data if r["created_at"].startswith(day) and r["conclusion"] == "success")
failed = sum(1 for r in data if r["created_at"].startswith(day) and r["conclusion"] == "failure")
print(ok, failed)
' "$TODAY")

echo "watchdog: day=${TODAY}  scheduler success=${OK}  failed=${FAILED}"

if [ "${OK:-0}" -ge 1 ]; then
  echo "OK — a pool post went out on ${TODAY}. No action."
  exit 0
fi

if [ "${FAILED:-0}" -ge 1 ]; then
  detail="a scheduler run today failed"
else
  detail="no scheduler run fired today (GitHub may have delayed the cron)"
fi
echo "MISS — ${detail}. Self-healing…"

# ---- SELF-HEAL: trigger the scheduler to publish the next pool post (with image).
heal_ok=0
if [ "${WATCHDOG_DRYRUN:-}" = "1" ]; then
  echo "DRY RUN — would dispatch telegram-scheduler.yml to self-heal."
  exit 0
fi
if curl -fsS -X POST "${AUTH[@]}" -H "Accept: application/vnd.github+json" \
     "${API}/actions/workflows/telegram-scheduler.yml/dispatches" -d '{"ref":"main"}' >/dev/null 2>&1; then
  echo "Self-heal: dispatched the scheduler to publish now."
  heal_ok=1
else
  echo "Self-heal FAILED: could not dispatch the scheduler."
fi

# ---- Durable record ONLY when we couldn't auto-recover (avoids a daily issue if cron is flaky).
if [ "$heal_ok" != "1" ]; then
  existing="$(curl -fsS "${AUTH[@]}" \
    "https://api.github.com/search/issues?q=repo:${GITHUB_REPOSITORY}+is:issue+is:open+in:title+watchdog+${TODAY}" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("total_count", 0))')"
  if [ "${existing:-0}" -lt 1 ]; then
    TITLE="⚠️ watchdog: post missing AND auto-recovery failed — ${TODAY}"
    BODY="On ${TODAY} (UTC) ${detail}, and the watchdog could not dispatch the scheduler to recover.

**Manual fix:** Actions → **Telegram Scheduler (queue)** → **Run workflow**.

_Opened by \`telegram-watchdog.yml\`._"
    payload="$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "body": sys.argv[2]}))' "$TITLE" "$BODY")"
    curl -fsS -X POST "${AUTH[@]}" -H "Accept: application/vnd.github+json" "${API}/issues" -d "$payload" >/dev/null
    echo "Opened a recovery-failed issue for ${TODAY}."
  fi
fi
