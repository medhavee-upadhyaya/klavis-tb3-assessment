import json
import os

import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://app:app_redis_pw@localhost:6379/0")

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
    return _client


def cache_key(tenant_id: str) -> str:
    """Cache key contract: fixed so ops tooling can address a tenant's
    cache entry without knowing how the value under it is encoded."""
    return f"cfg:{tenant_id}"


async def read_cached(tenant_id: str) -> dict | None:
    client = get_client()
    data = await client.hgetall(cache_key(tenant_id))
    if not data:
        return None
    return {
        "generation": int(data["generation"]),
        "model": data["model"],
        "prompt_version": data["prompt_version"],
        "tool_policy": json.loads(data["tool_policy"]),
        "fallback_chain": json.loads(data["fallback_chain"]),
        "limits": json.loads(data["limits"]),
    }


async def write_cache(tenant_id: str, cfg: dict) -> None:
    """Populate the read-through cache entry for a tenant.

    Field-level HSET calls keep each write small instead of re-serializing
    the whole hash for a single field change.
    """
    client = get_client()
    key = cache_key(tenant_id)
    await client.hset(key, "generation", cfg["generation"])
    await client.hset(key, "model", cfg["model"])
    await client.hset(key, "prompt_version", cfg["prompt_version"])
    await client.hset(key, "tool_policy", json.dumps(cfg["tool_policy"]))
    await client.hset(key, "fallback_chain", json.dumps(cfg["fallback_chain"]))
    await client.hset(key, "limits", json.dumps(cfg["limits"]))
