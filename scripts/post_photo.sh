#!/usr/bin/env bash
# Posts a photo with an optional caption to a Telegram channel via the Bot API.
# Required env:
#   TELEGRAM_BOT_TOKEN  - bot token (GitHub Actions secret)
#   TELEGRAM_CHAT_ID    - target chat/channel id, e.g. -1003765175397
# Inputs:
#   INPUT_PHOTO         - repo file path (e.g. images/vcm.png) OR a public http(s) URL
#   INPUT_CAPTION       - optional caption (HTML allowed, up to 1024 chars)
set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is not set}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID is not set}"

PHOTO="${INPUT_PHOTO:-}"
CAPTION="${INPUT_CAPTION:-}"
[ -n "$PHOTO" ] || { echo "No photo provided (set INPUT_PHOTO to a repo path or URL)." >&2; exit 1; }

# Telegram caption limit is 1024 characters.
CLEN=$(printf '%s' "$CAPTION" | wc -m | tr -d ' ')
echo "Caption length: ${CLEN} characters"
if [ "$CLEN" -gt 1024 ]; then
  echo "Caption length ${CLEN} exceeds Telegram's 1024-character limit." >&2
  exit 1
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto"

# Capture body + HTTP status without -f, so the Telegram error message is visible
# even on a 4xx (e.g. caption parse errors).
if printf '%s' "$PHOTO" | grep -qiE '^https?://'; then
  echo "Sending photo by URL: ${PHOTO}"
  RAW=$(curl -sS -w $'\n%{http_code}' -X POST "$API" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "photo=${PHOTO}" \
    --data-urlencode "caption=${CAPTION}" \
    --data-urlencode "parse_mode=HTML")
else
  [ -f "$PHOTO" ] || { echo "File not found in repo: ${PHOTO}" >&2; exit 1; }
  echo "Uploading photo file: ${PHOTO}"
  # --form-string sends values literally; -F would treat a leading '<' or '@'
  # in the caption (e.g. "<b>...") as a "read from file" directive.
  RAW=$(curl -sS -w $'\n%{http_code}' -X POST "$API" \
    --form-string "chat_id=${TELEGRAM_CHAT_ID}" \
    --form-string "caption=${CAPTION}" \
    --form-string "parse_mode=HTML" \
    -F "photo=@${PHOTO}")
fi

CODE=$(printf '%s' "$RAW" | tail -n1)
BODY=$(printf '%s' "$RAW" | sed '$d')
echo "HTTP ${CODE}"
echo "Telegram response: ${BODY}"
if ! printf '%s' "$BODY" | grep -q '"ok":true'; then
  echo "::error::Telegram sendPhoto failed (HTTP ${CODE}): ${BODY}"
  exit 1
fi
echo "Photo posted successfully."
