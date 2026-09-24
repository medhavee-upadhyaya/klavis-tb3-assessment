import json
import os

import asyncpg

# Writes go to the primary; config reads go to the streaming read replica.
PRIMARY_DATABASE_URL = os.environ.get(
    "PRIMARY_DATABASE_URL", "postgresql://app_writer:writer_pw@localhost:5432/gateway"
)
REPLICA_DATABASE_URL = os.environ.get(
    "REPLICA_DATABASE_URL", "postgresql://app_reader:reader_pw@localhost:5433/gateway"
)

_primary_pool: asyncpg.Pool | None = None
_replica_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def get_primary_pool() -> asyncpg.Pool:
    global _primary_pool
    if _primary_pool is None:
        _primary_pool = await asyncpg.create_pool(
            PRIMARY_DATABASE_URL, min_size=2, max_size=10, init=_init_connection
        )
    return _primary_pool


async def get_replica_pool() -> asyncpg.Pool:
    global _replica_pool
    if _replica_pool is None:
        _replica_pool = await asyncpg.create_pool(
            REPLICA_DATABASE_URL, min_size=2, max_size=10, init=_init_connection
        )
    return _replica_pool


async def fetch_config(tenant_id: str) -> asyncpg.Record | None:
    pool = await get_replica_pool()
    return await pool.fetchrow(
        """
        SELECT tenant_id, generation, model, prompt_version, tool_policy,
               fallback_chain, limits
        FROM tenant_configs
        WHERE tenant_id = $1
        """,
        tenant_id,
    )


async def apply_update(
    tenant_id: str,
    expected_generation: int,
    model: str,
    prompt_version: str,
    tool_policy: dict,
    fallback_chain: list,
    limits: dict,
) -> asyncpg.Record | None:
    pool = await get_primary_pool()
    return await pool.fetchrow(
        "SELECT * FROM apply_update($1, $2, $3, $4, $5, $6, $7)",
        tenant_id,
        expected_generation,
        model,
        prompt_version,
        tool_policy,
        fallback_chain,
        limits,
    )
