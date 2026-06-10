#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LAW_DATA_DIR="${LAW_DATA_DIR:-/app/legislation}"
SYNC_INTERVAL_DAYS="${SYNC_INTERVAL_DAYS:-15}"
STATE_DIR="$LAW_DATA_DIR/state"
LOCK_DIR="$STATE_DIR/sync.lock"
LAST_SYNC_FILE="$STATE_DIR/last_sync_epoch"

mkdir -p "$STATE_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another national law database sync is already running."
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

now_epoch="$(date +%s)"
interval_seconds="$((SYNC_INTERVAL_DAYS * 24 * 60 * 60))"
last_sync_epoch="0"

if [[ -f "$LAST_SYNC_FILE" ]]; then
  last_sync_epoch="$(cat "$LAST_SYNC_FILE")"
fi

if ! [[ "$last_sync_epoch" =~ ^[0-9]+$ ]]; then
  last_sync_epoch="0"
fi

elapsed_seconds="$((now_epoch - last_sync_epoch))"
if (( elapsed_seconds < interval_seconds )); then
  next_epoch="$((last_sync_epoch + interval_seconds))"
  echo "National law database sync is not due yet. Next eligible epoch: $next_epoch."
  exit 0
fi

"$ROOT_DIR/shell/update_national_law_db.sh" "$@"
printf '%s\n' "$now_epoch" > "$LAST_SYNC_FILE"
