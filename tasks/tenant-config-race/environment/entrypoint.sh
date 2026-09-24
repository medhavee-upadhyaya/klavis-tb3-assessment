#!/bin/bash
set -e

# PostgreSQL: a primary (port 5432, all writes) plus an asynchronous
# streaming read replica (port 5433, all config reads). The schema, roles
# and grants are provisioned here, not by the app:
#   app_writer -- primary only; may call public.apply_update() and nothing
#                 else on tenant_configs (no SELECT).
#   app_reader -- SELECT on tenant_configs; rejected by the primary's
#                 pg_hba, so it can only read from the replica.
if [ ! -d /var/lib/postgresql/15/replica ]; then
    service postgresql start
    for i in $(seq 1 60); do
        su postgres -c "pg_isready -p 5432" >/dev/null 2>&1 && break
        sleep 0.5
    done
    su postgres -c "pg_isready -p 5432" >/dev/null 2>&1 || { echo "postgres primary failed to start"; exit 1; }

    su postgres -c "psql -v ON_ERROR_STOP=1 -q" <<'SQL'
CREATE ROLE gateway_owner NOLOGIN;
CREATE ROLE app_writer LOGIN PASSWORD 'writer_pw';
CREATE ROLE app_reader LOGIN PASSWORD 'reader_pw';
CREATE ROLE replicator REPLICATION LOGIN PASSWORD 'repl_pw';
CREATE DATABASE gateway OWNER gateway_owner;
SQL

    su postgres -c "psql -v ON_ERROR_STOP=1 -q -d gateway" <<'SQL'
SET ROLE gateway_owner;
CREATE TABLE public.tenant_configs (
    tenant_id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    tool_policy JSONB NOT NULL,
    fallback_chain JSONB NOT NULL,
    limits JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO public.tenant_configs
    (tenant_id, generation, model, prompt_version, tool_policy, fallback_chain, limits)
SELECT t, 0, 'base-model', 'v0', '{"allowed_tools": []}', '["base-model"]', '{"max_tokens": 512}'
FROM unnest(ARRAY['tenant-a','tenant-b','tenant-c','tenant-d',
                  'tenant-e','tenant-f','tenant-g','tenant-h']) AS t;

CREATE FUNCTION public.apply_update(
    p_tenant_id TEXT, p_expected_generation INTEGER, p_model TEXT,
    p_prompt_version TEXT, p_tool_policy JSONB, p_fallback_chain JSONB, p_limits JSONB
) RETURNS TABLE (
    tenant_id TEXT, generation INTEGER, model TEXT, prompt_version TEXT,
    tool_policy JSONB, fallback_chain JSONB, limits JSONB
)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
    UPDATE public.tenant_configs AS t
       SET generation = t.generation + 1,
           model = p_model,
           prompt_version = p_prompt_version,
           tool_policy = p_tool_policy,
           fallback_chain = p_fallback_chain,
           limits = p_limits,
           updated_at = now()
     WHERE t.tenant_id = p_tenant_id AND t.generation = p_expected_generation
    RETURNING t.tenant_id, t.generation, t.model, t.prompt_version,
              t.tool_policy, t.fallback_chain, t.limits;
$$;
REVOKE ALL ON FUNCTION public.apply_update(TEXT, INTEGER, TEXT, TEXT, JSONB, JSONB, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.apply_update(TEXT, INTEGER, TEXT, TEXT, JSONB, JSONB, JSONB) TO app_writer;
REVOKE ALL ON public.tenant_configs FROM PUBLIC;
GRANT SELECT ON public.tenant_configs TO app_reader;
RESET ROLE;
SQL

    # app_reader may never read from the primary (first matching line wins).
    sed -i '1i local all app_reader reject\nhost all app_reader 0.0.0.0/0 reject\nhost all app_reader ::/0 reject' \
        /etc/postgresql/15/main/pg_hba.conf
    pg_ctlcluster 15 main reload

    pg_createcluster 15 replica --port 5433 >/dev/null
    rm -rf /var/lib/postgresql/15/replica
    su postgres -c "PGPASSWORD=repl_pw pg_basebackup -h 127.0.0.1 -p 5432 -U replicator \
        -D /var/lib/postgresql/15/replica -R -X stream -c fast" >/dev/null
    pg_ctlcluster 15 replica start
else
    service postgresql start
fi
for i in $(seq 1 60); do
    su postgres -c "pg_isready -p 5433" >/dev/null 2>&1 && break
    sleep 0.5
done
su postgres -c "pg_isready -p 5433" >/dev/null 2>&1 || { echo "postgres replica failed to start"; exit 1; }

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
redis-cli ACL SETUSER app on '>app_redis_pw' '~*' allcommands -@admin

/app/restart.sh

echo "environment ready"
exec tail -f /dev/null
