import asyncio

from db import get_pool

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tenant_configs (
    tenant_id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    tool_policy JSONB NOT NULL,
    fallback_chain JSONB NOT NULL,
    limits JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SEED_TENANTS = [
    "tenant-a",
    "tenant-b",
    "tenant-c",
    "tenant-d",
    "tenant-e",
    "tenant-f",
    "tenant-g",
    "tenant-h",
]


async def seed() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
        for tenant_id in SEED_TENANTS:
            await conn.execute(
                """
                INSERT INTO tenant_configs
                    (tenant_id, generation, model, prompt_version,
                     tool_policy, fallback_chain, limits)
                VALUES ($1, 0, 'base-model', 'v0', $2, $3, $4)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                tenant_id,
                {"allowed_tools": []},
                ["base-model"],
                {"max_tokens": 512},
            )


if __name__ == "__main__":
    asyncio.run(seed())
