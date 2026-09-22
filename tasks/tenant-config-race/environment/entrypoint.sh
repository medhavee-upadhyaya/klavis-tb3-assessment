#!/bin/bash
set -e

service postgresql start

for i in $(seq 1 30); do
    su postgres -c "pg_isready" >/dev/null 2>&1 && break
    sleep 0.5
done
su postgres -c "pg_isready" >/dev/null 2>&1 || { echo "postgres failed to start"; exit 1; }

su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='app'\"" | grep -q 1 || \
    su postgres -c "psql -c \"CREATE USER app WITH PASSWORD 'app_pw';\""
su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='gateway'\"" | grep -q 1 || \
    su postgres -c "psql -c \"CREATE DATABASE gateway OWNER app;\""

redis-server --daemonize yes --save "" --appendonly no
for i in $(seq 1 30); do
    redis-cli ping >/dev/null 2>&1 && break
    sleep 0.5
done
redis-cli ping >/dev/null 2>&1 || { echo "redis failed to start"; exit 1; }

# The app authenticates as its own dedicated ACL user (not the default
# user) so that admin tooling can disable/kill *only* the app's Redis
# access (to simulate a real app-side outage) without touching Redis's
# own default-user access.
redis-cli ACL SETUSER app on '>app_redis_pw' '~*' allcommands

/app/restart.sh

echo "environment ready"
exec tail -f /dev/null
