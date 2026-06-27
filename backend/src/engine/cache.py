import hashlib
import json
import os

import redis.asyncio as aioredis


def stable_hash(inputs: dict) -> str:
    raw = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def get_cached_result(
    workflow_name: str, inputs: dict, ttl: int = 3600
) -> str | None:
    key = f"AutoSteer:cache:{workflow_name}:{stable_hash(inputs)}"
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    try:
        val = await r.get(key)
        return val.decode() if val else None
    finally:
        await r.close()


async def set_cached_result(
    workflow_name: str, inputs: dict, result: str, ttl: int = 3600
) -> None:
    key = f"AutoSteer:cache:{workflow_name}:{stable_hash(inputs)}"
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    try:
        await r.setex(key, ttl, result)
    finally:
        await r.close()
