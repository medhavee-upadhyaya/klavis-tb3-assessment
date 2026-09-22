#!/usr/bin/env bash
set -e

if [ -f /app/uvicorn.pid ]; then
    kill "$(cat /app/uvicorn.pid)" 2>/dev/null || true
    rm -f /app/uvicorn.pid
    for _ in $(seq 1 50); do
        curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1 || break
        sleep 0.1
    done
fi

cd /app
DATABASE_URL="${DATABASE_URL:-postgresql://app:app_pw@localhost:5432/gateway}" \
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 \
    > /app/uvicorn.log 2>&1 &
echo $! > /app/uvicorn.pid

for _ in $(seq 1 50); do
    if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
        echo "service is up"
        exit 0
    fi
    sleep 0.2
done

echo "service failed to start" >&2
cat /app/uvicorn.log >&2
exit 1
