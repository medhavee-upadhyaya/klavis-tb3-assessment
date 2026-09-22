import json
import os

import asyncpg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://app:app_pw@localhost:5432/gateway"
)

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL, min_size=2, max_size=10, init=_init_connection
        )
    return _pool


async def fetch_config(tenant_id: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow(
        """
        SELECT tenant_id, generation, model, prompt_version, tool_policy,
               fallback_chain, limits
        FROM tenant_configs
        WHERE tenant_id = $1
        """,
        tenant_id,
    )


async def fetch_generation(tenant_id: str) -> int | None:
    """Cheap, single-column freshness check -- lets a caller confirm a
    cached value isn't stale without paying for the full row (and its
    JSONB fields) on every read."""
    pool = await get_pool()
    return await pool.fetchval(
        "SELECT generation FROM tenant_configs WHERE tenant_id = $1", tenant_id
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
    pool = await get_pool()
    return await pool.fetchrow(
        """
        UPDATE tenant_configs
        SET generation = generation + 1,
            model = $2,
            prompt_version = $3,
            tool_policy = $4,
            fallback_chain = $5,
            limits = $6,
            updated_at = now()
        WHERE tenant_id = $1 AND generation = $7
        RETURNING tenant_id, generation, model, prompt_version, tool_policy,
                  fallback_chain, limits
        """,
        tenant_id,
        model,
        prompt_version,
        tool_policy,
        fallback_chain,
        limits,
        expected_generation,
    )
