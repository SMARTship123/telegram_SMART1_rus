#!/usr/bin/env bash
# Publishes the NEXT queued post to Telegram, then archives it.
#
# Queue item = queue/NNNN-slug.md, a small header then a `---` line then the body:
#
#     type: photo            # photo | text   (default: text)
#     image: images/foo.png  # required when type=photo
#     ---
#     <body: HTML caption (photo) or message text>
#
# Items are published in filename order, so zero-padded numeric prefixes
# (0001-, 0002-, …) set the schedule. The send reuses the proven
# scripts/post_photo.sh and scripts/post_telegram.sh (length checks, HTML,
# error surfacing). On success the file is moved into queue/published/ with a
# UTC timestamp. A FAILED send leaves the item in the queue (set -e stops before
# the archive step), so the next run retries it rather than skipping content.
#
# Env:
#   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  - required (provided by the workflow)
#   DRY_RUN=1                             - parse and print only; do not send or archive
#
# Writes `published=<path>` to $GITHUB_OUTPUT (empty when the queue is empty)
# so the workflow knows whether there is an archive commit to make.
set -euo pipefail

QUEUE_DIR="queue"
ARCHIVE_DIR="queue/published"

emit() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "published=$1" >> "$GITHUB_OUTPUT" || true; }

NEXT=$(find "$QUEUE_DIR" -maxdepth 1 -name '*.md' -type f 2>/dev/null | sort | head -n1 || true)
if [ -z "${NEXT:-}" ]; then
  echo "Queue is empty — nothing to publish."
  emit ""
  exit 0
fi
echo "Next queue item: $NEXT"

# Header = everything before the first `---` line; body = everything after it.
header() { awk '/^---[[:space:]]*$/{exit} {print}' "$NEXT"; }
TYPE=$(header  | sed -n 's/^type:[[:space:]]*//p'  | head -n1)
IMAGE=$(header | sed -n 's/^image:[[:space:]]*//p' | head -n1)
BODY=$(awk 'body{print} /^---[[:space:]]*$/{body=1}' "$NEXT")
TYPE="${TYPE:-text}"

if [ -z "${BODY//[$' \t\n']/}" ]; then
  echo "Queue item $NEXT has an empty body." >&2
  exit 1
fi

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "── DRY RUN ─────────────────────────────"
  echo "type : $TYPE"
  echo "image: ${IMAGE:-(none)}"
  echo "body :"
  printf '%s\n' "$BODY"
  echo "────────────────────────────────────────"
  echo "(dry run — not sending, not archiving)"
  exit 0
fi

case "$TYPE" in
  photo)
    [ -n "$IMAGE" ] || { echo "type=photo but no 'image:' in $NEXT" >&2; exit 1; }
    [ -f "$IMAGE" ] || { echo "image not found: $IMAGE" >&2; exit 1; }
    echo "Publishing PHOTO: $IMAGE"
    INPUT_PHOTO="$IMAGE" INPUT_CAPTION="$BODY" bash scripts/post_photo.sh
    ;;
  text)
    echo "Publishing TEXT message"
    INPUT_MESSAGE="$BODY" bash scripts/post_telegram.sh
    ;;
  *)
    echo "Unknown type '$TYPE' in $NEXT (use photo|text)." >&2
    exit 1
    ;;
esac

mkdir -p "$ARCHIVE_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$ARCHIVE_DIR/$(basename "${NEXT%.md}").$STAMP.md"
git mv "$NEXT" "$DEST" 2>/dev/null || mv "$NEXT" "$DEST"
echo "Archived published item to $DEST"
emit "$DEST"
