#!/bin/sh
set -e

# Substitute PORT environment variable in nginx config
export PORT=${PORT:-80}
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g 'daemon off;'
