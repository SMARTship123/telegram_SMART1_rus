#!/usr/bin/env bash
# Posts a message to a Telegram channel via the Bot API.
# Required env:
#   TELEGRAM_BOT_TOKEN  - bot token (store as a GitHub Actions secret)
#   TELEGRAM_CHAT_ID    - target chat/channel id, e.g. -1003765175397
# Optional env:
#   INPUT_MESSAGE       - the post text; if empty, falls back to posts/latest.txt
set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is not set}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID is not set}"

MESSAGE="${INPUT_MESSAGE:-}"
if [ -z "${MESSAGE}" ]; then
  if [ -f posts/latest.txt ]; then
    MESSAGE="$(cat posts/latest.txt)"
  else
    echo "No message provided and posts/latest.txt is missing." >&2
    exit 1
  fi
fi

# Validate length (Telegram caps at 4096; the editorial brief asks for 280-380).
LEN=$(printf '%s' "$MESSAGE" | wc -m | tr -d ' ')
echo "Message length: ${LEN} characters"
if [ "$LEN" -lt 1 ] || [ "$LEN" -gt 4096 ]; then
  echo "Message length ${LEN} is out of Telegram's allowed range." >&2
  exit 1
fi

# parse_mode=HTML matches the editorial standard (key figure in <b>…</b>) and the
# photo script. Without it Telegram renders the literal tags.
RESPONSE=$(curl -fsS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "parse_mode=HTML" \
  --data-urlencode "text=${MESSAGE}")

echo "Telegram response: ${RESPONSE}"
echo "$RESPONSE" | grep -q '"ok":true' || { echo "Telegram API reported failure." >&2; exit 1; }
echo "Posted successfully."
