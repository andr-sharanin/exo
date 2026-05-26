"""
Publish SSE events to a user's browser from anywhere in the backend.

Usage:
    from app.services.event_publisher import publish
    await publish(user_id, "plan_ready", {"plan_id": "..."})

Events are written to Redis pub/sub channel user:{user_id}:events.
The SSE endpoint in api/v1/sse.py broadcasts them to the connected browser.
"""
import json

import redis.asyncio as aioredis

from app.api.v1.sse import get_redis_pool


async def publish(user_id: str, event_type: str, payload: dict | None = None) -> None:
    """Push a typed event to the user's SSE stream."""
    r = aioredis.Redis(connection_pool=get_redis_pool())
    data = json.dumps({"type": event_type, "payload": payload or {}}).encode()
    await r.publish(f"user:{user_id}:events", data)
    # No r.aclose() — shared pool; connection returns to pool automatically.
