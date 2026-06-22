#!/usr/bin/env bash
set -euo pipefail

# Daily sync: GDrive canonical project -> local workspace project
# Default source (canonical GDrive path agreed in memory):
#   /home/dung/gdrive_mount/openclaw/projects/MOSQUITO_trap_dashboard
# Default destination:
#   /home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard

SRC="${1:-/home/dung/gdrive_mount/openclaw/projects/MOSQUITO_trap_dashboard}"
DST="${2:-/home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard}"
HEALTH_URL="${3:-http://127.0.0.1:8787/dashboard_v9.html}"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${DST}/logs"
LOG_FILE="${LOG_DIR}/gdrive_sync_daily.log"

mkdir -p "$DST" "$LOG_DIR"

echo "[$(date '+%F %T %Z')] START sync SRC=$SRC -> DST=$DST" | tee -a "$LOG_FILE"

if [[ ! -d "$SRC" ]]; then
  echo "[$(date '+%F %T %Z')] ERROR: source path not found: $SRC" | tee -a "$LOG_FILE"
  exit 1
fi

# Safe-by-default sync (non-destructive): no --delete
rsync -avh \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.tmp' \
  "$SRC/" "$DST/" | tee -a "$LOG_FILE"

# Optional quick health check
if command -v curl >/dev/null 2>&1; then
  code="$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || true)"
  echo "[$(date '+%F %T %Z')] HEALTH $HEALTH_URL -> HTTP $code" | tee -a "$LOG_FILE"
fi

echo "[$(date '+%F %T %Z')] DONE sync" | tee -a "$LOG_FILE"

echo "[OK] Synced successfully at $TS"
