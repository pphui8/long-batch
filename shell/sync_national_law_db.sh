#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

LOG_DIR="${LOG_DIR:-logs}"
mkdir -p "$LOG_DIR"

"$PYTHON_BIN" -m domain.sync_national_law_db "$@" 2>&1 | tee -a "$LOG_DIR/sync_national_law_db.log"
