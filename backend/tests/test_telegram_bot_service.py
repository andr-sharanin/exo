"""
Unit tests for telegram_bot.py helpers.

Redis is replaced with an in-memory stub.
No real Telegram API calls — send_message / answer_callback are tested
against a mock httpx transport.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.telegram_bot import (
    create_link_token,
    consume_link_token,
    get_state,
    set_state,
    clear_state,
    inline_keyboard,
    send_message,
    answer_callback,
)


# ── Redis stub ────────────────────────────────────────────────────────────────

class _FakeRedis:
    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self._store[key] = value

    async def delete(self, key: str):
        self._store.pop(key, None)


# ── create_link_token ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_link_token_returns_string():
    redis = _FakeRedis()
    token = await create_link_token(redis, "user-1", "tenant-1")
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_create_link_token_stores_user_and_tenant():
    redis = _FakeRedis()
    token = await create_link_token(redis, "user-42", "tenant-99")
    key = f"tg:link:{token}"
    stored = json.loads(redis._store[key])
    assert stored["user_id"] == "user-42"
    assert stored["tenant_id"] == "tenant-99"


@pytest.mark.asyncio
async def test_create_link_token_each_call_unique():
    redis = _FakeRedis()
    t1 = await create_link_token(redis, "u1", "t1")
    t2 = await create_link_token(redis, "u1", "t1")
    assert t1 != t2


# ── consume_link_token ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consume_link_token_returns_payload():
    redis = _FakeRedis()
    token = await create_link_token(redis, "user-7", "tenant-3")
    payload = await consume_link_token(redis, token)
    assert payload is not None
    assert payload["user_id"] == "user-7"
    assert payload["tenant_id"] == "tenant-3"


@pytest.mark.asyncio
async def test_consume_link_token_deletes_after_use():
    redis = _FakeRedis()
    token = await create_link_token(redis, "user-7", "tenant-3")
    await consume_link_token(redis, token)
    # Token should be gone now
    second = await consume_link_token(redis, token)
    assert second is None


@pytest.mark.asyncio
async def test_consume_link_token_returns_none_for_unknown():
    redis = _FakeRedis()
    result = await consume_link_token(redis, "no-such-token")
    assert result is None


# ── get_state / set_state / clear_state ──────────────────────────────────────

@pytest.mark.asyncio
async def test_get_state_returns_idle_when_empty():
    redis = _FakeRedis()
    state = await get_state(redis, chat_id=111)
    assert state["state"] == "idle"
    assert state["data"] == {}


@pytest.mark.asyncio
async def test_set_and_get_state_roundtrip():
    redis = _FakeRedis()
    await set_state(redis, chat_id=222, state="waiting_title", data={"step": 1})
    state = await get_state(redis, chat_id=222)
    assert state["state"] == "waiting_title"
    assert state["data"]["step"] == 1


@pytest.mark.asyncio
async def test_set_state_with_no_data_defaults_to_empty_dict():
    redis = _FakeRedis()
    await set_state(redis, chat_id=333, state="confirming")
    state = await get_state(redis, chat_id=333)
    assert state["data"] == {}


@pytest.mark.asyncio
async def test_clear_state_resets_to_idle():
    redis = _FakeRedis()
    await set_state(redis, chat_id=444, state="active", data={"key": "val"})
    await clear_state(redis, chat_id=444)
    state = await get_state(redis, chat_id=444)
    assert state["state"] == "idle"


@pytest.mark.asyncio
async def test_clear_state_on_nonexistent_key_is_safe():
    redis = _FakeRedis()
    # Should not raise
    await clear_state(redis, chat_id=999)


# ── inline_keyboard ───────────────────────────────────────────────────────────

def test_inline_keyboard_structure():
    markup = inline_keyboard([
        [("Yes ✅", "action:yes"), ("No ❌", "action:no")],
        [("Cancel", "action:cancel")],
    ])
    assert "inline_keyboard" in markup
    rows = markup["inline_keyboard"]
    assert len(rows) == 2
    assert rows[0][0]["text"] == "Yes ✅"
    assert rows[0][0]["callback_data"] == "action:yes"
    assert rows[1][0]["callback_data"] == "action:cancel"


def test_inline_keyboard_empty_rows():
    markup = inline_keyboard([])
    assert markup["inline_keyboard"] == []


# ── send_message fire-and-forget ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_message_does_not_raise_on_http_error():
    import httpx

    async def _fail(*args, **kwargs):
        raise httpx.ConnectError("Network error")

    with patch("httpx.AsyncClient.post", new=_fail):
        # Should silently swallow the error
        await send_message("fake_token", chat_id=12345, text="Hello")


@pytest.mark.asyncio
async def test_send_message_posts_to_correct_url():
    call_args = {}

    async def _capture(url, **kwargs):
        call_args["url"] = url
        call_args["payload"] = kwargs.get("json", {})
        return MagicMock()

    with patch("httpx.AsyncClient.post", new=_capture):
        await send_message("BOT_TOKEN", chat_id=99, text="Hi there")

    assert "BOT_TOKEN" in call_args["url"]
    assert "sendMessage" in call_args["url"]
    assert call_args["payload"]["chat_id"] == 99
    assert call_args["payload"]["text"] == "Hi there"


@pytest.mark.asyncio
async def test_answer_callback_does_not_raise_on_error():
    import httpx

    async def _fail(*args, **kwargs):
        raise httpx.TimeoutException("Timeout")

    with patch("httpx.AsyncClient.post", new=_fail):
        await answer_callback("token", callback_id="cb_1", text="Ok")
