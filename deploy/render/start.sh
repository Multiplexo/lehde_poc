#!/usr/bin/env bash
# Starts nginx and the API in one container; exits when either stops.
set -euo pipefail
cd /app

if [[ -z "${DEMO_USER:-}" || -z "${DEMO_PASSWORD:-}" ]]; then
    echo "DEMO_USER and DEMO_PASSWORD must be set; refusing to start without a login" >&2
    exit 1
fi
printf '%s:%s\n' "$DEMO_USER" "$(openssl passwd -apr1 "$DEMO_PASSWORD")" > /etc/nginx/htpasswd

.venv/bin/alembic upgrade head

nginx -g "daemon off;" &
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers &

wait -n
exit 1
