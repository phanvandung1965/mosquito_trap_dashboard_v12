#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash deploy_mosquito_domain.sh [DOMAIN] [UPSTREAM_PORT]
# Example:
#   sudo bash deploy_mosquito_domain.sh mosquito.vietsunbirdnest.com.au 8787

DOMAIN="${1:-mosquito.vietsunbirdnest.com.au}"
UPSTREAM_PORT="${2:-8787}"
UPSTREAM="127.0.0.1:${UPSTREAM_PORT}"
CONF="/etc/nginx/sites-available/${DOMAIN}.conf"
LINK="/etc/nginx/sites-enabled/${DOMAIN}.conf"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "[ERROR] Please run as root (sudo)."
  exit 1
fi

has_systemd() {
  command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]
}

enable_nginx() {
  if has_systemd; then
    systemctl enable nginx >/dev/null 2>&1 || true
  fi
}

restart_nginx() {
  if has_systemd; then
    systemctl restart nginx
  elif command -v service >/dev/null 2>&1; then
    service nginx restart
  else
    nginx -s reload >/dev/null 2>&1 || true
  fi
}

reload_nginx() {
  if has_systemd; then
    systemctl reload nginx
  elif command -v service >/dev/null 2>&1; then
    service nginx reload
  else
    nginx -s reload >/dev/null 2>&1 || true
  fi
}

if ! command -v nginx >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y nginx
fi

if ! command -v certbot >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y certbot python3-certbot-nginx
fi

cat > "$CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://${UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "$CONF" "$LINK"
nginx -t
enable_nginx
restart_nginx

# SSL
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@vietsunbirdnest.com.au --redirect

nginx -t
reload_nginx

echo "[OK] Deployment completed for https://${DOMAIN} -> ${UPSTREAM}"

# quick checks
curl -I "http://${DOMAIN}" | head -n 5 || true
curl -I "https://${DOMAIN}" | head -n 5 || true
curl -I "http://127.0.0.1:${UPSTREAM_PORT}/dashboard_v9.html" | head -n 5 || true

# firewall note (if UFW enabled)
if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

echo "[DONE]"
