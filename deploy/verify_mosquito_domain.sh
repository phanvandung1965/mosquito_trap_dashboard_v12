#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-mosquito.vietsunbirdnest.com.au}"
PORT="${2:-8787}"

echo "== DNS =="
getent hosts "$DOMAIN" || true

python3 - <<PY
import socket
host='${DOMAIN}'
try:
    print('DNS:', socket.gethostbyname_ex(host))
except Exception as e:
    print('DNS_ERR:', e)
PY

echo "\n== Local service =="
curl -sSI "http://127.0.0.1:${PORT}/dashboard_v9.html" | head -n 10 || true

echo "\n== Public HTTP/HTTPS =="
curl -sSI "http://${DOMAIN}" | head -n 10 || true
curl -sSI "https://${DOMAIN}" | head -n 10 || true

echo "\n== Nginx listeners =="
ss -ltnp | grep -E ':80 |:443 ' || true

echo "\n== Nginx status =="
systemctl status nginx --no-pager -l 2>/dev/null | sed -n '1,20p' || echo "(systemctl unavailable or no permission)"

echo "\n[DONE]"
