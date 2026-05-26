"""
Server-Sent Events endpoint.

Each authenticated user has a personal Redis pub/sub channel:
    user:{user_id}:events

All backend services publish to this channel via event_publisher.publish().
The browser connects to /api/v1/events/stream via the Next.js SSE proxy
at /api/sse (which adds the Bearer token since EventSource has no header API).

Connection pool is module-level — shared across all concurrent SSE clients.
"""
import asyncio
import json
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.auth import CurrentUser
from app.core.config import settings

router = APIRouter(prefix="/events", tags=["sse"])

# Shared pool: created once per process, reused by all SSE and publisher connections.
# max_connections covers concurrent SSE clients + internal publishers.
_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=500,
            decode_responses=False,
        )
    return _pool


async def _stream(user_id: str, request: Request) -> AsyncGenerator[bytes, None]:
    r = aioredis.Redis(connection_pool=get_redis_pool())
    pubsub = r.pubsub()
    channel = f"user:{user_id}:events"
    await pubsub.subscribe(channel)

    try:
        # Immediate handshake — lets the frontend know the connection is live
        yield b"data: " + json.dumps({"type": "connected"}).encode() + b"\n\n"

        while True:
            # Detect browser tab close / network drop without blocking the loop
            if await request.is_disconnected():
                break

            msg = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=20.0,  # yields control every 20 s at most
            )

            if msg and isinstance(msg["data"], bytes):
                yield b"data: " + msg["data"] + b"\n\n"
            else:
                # SSE comment line — keeps connection alive through Nginx / CDN
                yield b": keepalive\n\n"

            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        # Client disconnected — FastAPI cancels the generator coroutine
        pass
    finally:
        # Release pubsub subscription and return connection to pool.
        # DO NOT call r.aclose() — that would close the shared pool connection.
        await pubsub.unsubscribe(channel)
        await pubsub.reset()


@router.get("/stream")
async def event_stream(request: Request, user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(
        _stream(str(user.user_id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering
            "Connection": "keep-alive",
        },
    )
