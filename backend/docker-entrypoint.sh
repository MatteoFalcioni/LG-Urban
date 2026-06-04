#!/bin/sh
set -e

# Railway injects PORT at runtime. Some existing Railway domains can keep a
# stale target port, so keep uvicorn on PORT and forward common target ports.
export PORT=${PORT:-8000}

echo "Running database migrations"
alembic upgrade head

SEEN_PORTS=""
for candidate_port in "${PORT}" 8000 8080 80; do
    case " ${SEEN_PORTS} " in
        *" ${candidate_port} "*) continue ;;
    esac
    SEEN_PORTS="${SEEN_PORTS} ${candidate_port}"

    if [ "${candidate_port}" != "${PORT}" ]; then
        echo "Forwarding 0.0.0.0:${candidate_port} -> 127.0.0.1:${PORT}"
        socat TCP-LISTEN:"${candidate_port}",fork,reuseaddr TCP:127.0.0.1:"${PORT}" &
    fi
done

echo "Starting backend on 0.0.0.0:${PORT}"
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
