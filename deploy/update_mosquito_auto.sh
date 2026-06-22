#!/usr/bin/env bash
set -euo pipefail

# Interactive helper to locate the mosquito_trap_dashboard project on the current host,
# then run deploy + verify using the project's own deploy scripts.
#
# Usage:
#   bash update_mosquito_auto.sh
#   bash update_mosquito_auto.sh --domain mosquito.vietsunbirdnest.com.au --port 7807
#   bash update_mosquito_auto.sh --project /home/dung/projects/mosquito_trap_dashboard --domain mosquito.vietsunbirdnest.com.au --port 7807

DOMAIN="mosquito.vietsunbirdnest.com.au"
PORT="7807"
PROJECT_ROOT=""
AUTO_YES="0"

usage() {
  cat <<'EOF'
Usage:
  bash update_mosquito_auto.sh [options]

Options:
  --domain DOMAIN     Domain to deploy (default: mosquito.vietsunbirdnest.com.au)
  --port PORT         Upstream app port (default: 7807)
  --project PATH      Project root path (example: /home/dung/projects/mosquito_trap_dashboard)
  --yes               Skip final confirmation prompt
  -h, --help          Show help

Examples:
  bash update_mosquito_auto.sh
  bash update_mosquito_auto.sh --port 7807
  bash update_mosquito_auto.sh --project /home/dung/projects/mosquito_trap_dashboard --yes
EOF
}

log() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

err() {
  printf '[ERROR] %s\n' "$*" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:?Missing value for --domain}"
      shift 2
      ;;
    --port)
      PORT="${2:?Missing value for --port}"
      shift 2
      ;;
    --project)
      PROJECT_ROOT="${2:?Missing value for --project}"
      shift 2
      ;;
    --yes)
      AUTO_YES="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

require_file() {
  local file="$1"
  [[ -f "$file" ]] || { err "Missing file: $file"; exit 1; }
}

find_candidates() {
  local -a roots=(
    "/home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard"
    "/home/dung/projects/mosquito_trap_dashboard"
    "/home/dung/mosquito_trap_dashboard"
    "/home/dung/vp1_data_hot/projects/MOSQUITO_trap_dashboard"
  )

  local -a found=()
  local root
  for root in "${roots[@]}"; do
    if [[ -f "$root/deploy/deploy_mosquito_domain.sh" ]]; then
      found+=("$root")
    fi
  done

  if command -v find >/dev/null 2>&1; then
    while IFS= read -r path; do
      local candidate
      candidate="$(dirname "$(dirname "$path")")"
      [[ -d "$candidate" ]] || continue
      if [[ ! " ${found[*]} " =~ " ${candidate} " ]]; then
        found+=("$candidate")
      fi
    done < <(find /home/dung -type f -name 'deploy_mosquito_domain.sh' 2>/dev/null | sort)
  fi

  printf '%s\n' "${found[@]}"
}

choose_project() {
  local -a candidates=()
  mapfile -t candidates < <(find_candidates)

  if [[ ${#candidates[@]} -eq 0 ]]; then
    err "Không tìm thấy project có file deploy_mosquito_domain.sh trong /home/dung"
    exit 1
  fi

  if [[ ${#candidates[@]} -eq 1 ]]; then
    PROJECT_ROOT="${candidates[0]}"
    log "Auto chọn project: $PROJECT_ROOT"
    return
  fi

  echo "Chọn project cần deploy/update:"
  local i=1
  for item in "${candidates[@]}"; do
    printf '  %d) %s\n' "$i" "$item"
    i=$((i + 1))
  done

  local choice
  while true; do
    read -rp "Nhập số [1-${#candidates[@]}]: " choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#candidates[@]} )); then
      PROJECT_ROOT="${candidates[$((choice - 1))]}"
      break
    fi
    warn "Lựa chọn không hợp lệ."
  done
}

if [[ -z "$PROJECT_ROOT" ]]; then
  choose_project
fi

PROJECT_ROOT="$(realpath "$PROJECT_ROOT")"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
DEPLOY_SCRIPT="$DEPLOY_DIR/deploy_mosquito_domain.sh"
VERIFY_SCRIPT="$DEPLOY_DIR/verify_mosquito_domain.sh"

require_file "$DEPLOY_SCRIPT"
require_file "$VERIFY_SCRIPT"

CURRENT_HOST="$(hostname 2>/dev/null || echo unknown-host)"

log "Project root : $PROJECT_ROOT"
log "Deploy dir   : $DEPLOY_DIR"
log "Current host : $CURRENT_HOST"
log "Domain       : $DOMAIN"
log "Upstream port: $PORT"

echo
cat <<EOF
[MACHINE GUIDE]
- Chạy script này trên máy đang chứa project nguồn để deploy (máy hiện tại: $CURRENT_HOST)
- Script deploy Nginx/domain sẽ tác động lên CHÍNH máy bạn đang chạy lệnh này.
- Vì vậy:
  1) Nếu muốn publish domain trên VPS -> hãy SSH vào VPS rồi chạy script tại đó.
  2) Nếu đang đứng ở máy local/dev -> chỉ nên dùng để chuẩn bị/kiểm tra, không nên deploy domain production tại đây.

[LỆNH CHẠY TỪ MÁY NÀO]
- Chạy từ MÁY HIỆN TẠI ($CURRENT_HOST):
    cd "$DEPLOY_DIR"
    bash update_mosquito_auto.sh --project "$PROJECT_ROOT" --domain "$DOMAIN" --port "$PORT"

- Nếu muốn chuyển code TỪ MÁY HIỆN TẠI ($CURRENT_HOST) lên VPS trước, dùng ví dụ:
    rsync -avz --progress "$PROJECT_ROOT/" user@YOUR_VPS:/home/dung/projects/mosquito_trap_dashboard/

- Sau đó SSH vào VPS và chạy TRÊN VPS:
    cd /home/dung/projects/mosquito_trap_dashboard/deploy
    bash update_mosquito_auto.sh --project /home/dung/projects/mosquito_trap_dashboard --domain "$DOMAIN" --port "$PORT"
EOF
echo

if [[ "$AUTO_YES" != "1" ]]; then
  read -rp "Tiếp tục deploy + verify TRÊN MÁY NÀY ($CURRENT_HOST)? [y/N]: " confirm
  case "$confirm" in
    y|Y|yes|YES) ;;
    *)
      warn "Đã hủy."
      exit 0
      ;;
  esac
fi

cd "$DEPLOY_DIR"

log "Bắt đầu deploy trên host: $CURRENT_HOST ..."
sudo bash "$DEPLOY_SCRIPT" "$DOMAIN" "$PORT"

log "Bắt đầu verify trên host: $CURRENT_HOST ..."
bash "$VERIFY_SCRIPT" "$DOMAIN" "$PORT"

cat <<EOF

[OK] Hoàn tất trên host: $CURRENT_HOST
Lần sau chỉ cần chạy TRÊN CHÍNH MÁY MUỐN DEPLOY:
  cd "$DEPLOY_DIR"
  bash update_mosquito_auto.sh

Hoặc chạy thẳng:
  bash "$DEPLOY_DIR/update_mosquito_auto.sh" --yes
EOF
