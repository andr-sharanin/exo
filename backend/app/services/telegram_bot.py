"""
Telegram Bot v2 — helpers for sending messages and FSM state management.

State is stored in Redis under key `tg:state:{chat_id}` (TTL 10 min).
Link tokens are stored under `tg:link:{token}` (TTL 10 min).
"""
import json
import secrets
from datetime import datetime, timezone
from typing import Any

import httpx

_TG_API = "https://api.telegram.org/bot{token}/{method}"
_STATE_TTL = 600   # 10 min FSM state
_LINK_TTL = 600    # 10 min link token


# ── Telegram API ─────────────────────────────────────────────────────────────

async def send_message(bot_token: str, chat_id: int, text: str, **kwargs: Any) -> None:
    """Fire-and-forget sendMessage. Ignores errors to keep webhook response fast."""
    url = _TG_API.format(token=bot_token, method="sendMessage")
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", **kwargs}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(url, json=payload)
        except Exception:
            pass  # never let Telegram delivery failures break the webhook


async def answer_callback(bot_token: str, callback_id: str, text: str = "") -> None:
    url = _TG_API.format(token=bot_token, method="answerCallbackQuery")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(url, json={"callback_query_id": callback_id, "text": text})
        except Exception:
            pass


async def edit_message_text(
    bot_token: str, chat_id: int, message_id: int, text: str, **kwargs: Any
) -> None:
    url = _TG_API.format(token=bot_token, method="editMessageText")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(url, json={
                "chat_id": chat_id, "message_id": message_id,
                "text": text, "parse_mode": "HTML", **kwargs
            })
        except Exception:
            pass


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> dict:
    """Build inline_keyboard reply_markup from rows of (label, callback_data) tuples."""
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in rows
        ]
    }


# ── Redis FSM state ──────────────────────────────────────────────────────────

async def get_state(redis, chat_id: int) -> dict:
    raw = await redis.get(f"tg:state:{chat_id}")
    return json.loads(raw) if raw else {"state": "idle", "data": {}}


async def set_state(redis, chat_id: int, state: str, data: dict | None = None) -> None:
    payload = {"state": state, "data": data or {}}
    await redis.setex(f"tg:state:{chat_id}", _STATE_TTL, json.dumps(payload))


async def clear_state(redis, chat_id: int) -> None:
    await redis.delete(f"tg:state:{chat_id}")


# ── Link token ───────────────────────────────────────────────────────────────

async def create_link_token(redis, user_id: str, tenant_id: str) -> str:
    token = secrets.token_urlsafe(16)
    await redis.setex(
        f"tg:link:{token}",
        _LINK_TTL,
        json.dumps({"user_id": user_id, "tenant_id": tenant_id}),
    )
    return token


async def consume_link_token(redis, token: str) -> dict | None:
    """Returns {user_id, tenant_id} and deletes the token, or None if expired/invalid."""
    raw = await redis.get(f"tg:link:{token}")
    if not raw:
        return None
    await redis.delete(f"tg:link:{token}")
    return json.loads(raw)
