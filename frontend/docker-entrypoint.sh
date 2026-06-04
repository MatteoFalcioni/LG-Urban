#!/bin/sh
set -e

# Substitute PORT environment variable in nginx config.
# Railway injects PORT at runtime; 8080 is only a local/container fallback.
export PORT=${PORT:-8080}

LISTEN_DIRECTIVES="    listen 0.0.0.0:${PORT};"
for candidate_port in 80 8080 3000 4173 5173; do
    if [ "${candidate_port}" != "${PORT}" ]; then
        LISTEN_DIRECTIVES="${LISTEN_DIRECTIVES}
    listen 0.0.0.0:${candidate_port};"
    fi
done
export LISTEN_DIRECTIVES

envsubst '${LISTEN_DIRECTIVES}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting nginx with:"
printf '%s\n' "${LISTEN_DIRECTIVES}"
nginx -t

# Start nginx.
exec nginx -g 'daemon off;'
