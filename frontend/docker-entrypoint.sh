#!/bin/sh
set -e

# Substitute PORT environment variable in nginx config.
# Railway injects PORT at runtime; 8080 is only a local/container fallback.
export PORT=${PORT:-8080}
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting nginx on 0.0.0.0:${PORT}"
nginx -t

# Start nginx.
exec nginx -g 'daemon off;'
