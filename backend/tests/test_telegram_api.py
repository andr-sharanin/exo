"""
E2E tests for Phase 9: Telegram webhook endpoint.
Uses a mock Update payload — no real Telegram calls.
"""
import pytest
from httpx import AsyncClient


def _telegram_update(text: str = "/capture Buy milk", chat_id: int = 12345) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": chat_id, "first_name": "Test", "is_bot": False},
            "chat": {"id": chat_id, "type": "private"},
            "date": 1700000000,
            "text": text,
        },
    }


class TestTelegramWebhook:
    async def test_webhook_returns_200(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/telegram/webhook",
            json=_telegram_update(),
        )
        assert r.status_code == 200

    async def test_non_capture_command_returns_200(
        self, client: AsyncClient
    ) -> None:
        r = await client.post(
            "/api/v1/telegram/webhook",
            json=_telegram_update(text="Hello, any message"),
        )
        assert r.status_code == 200

    async def test_empty_update_returns_200(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/telegram/webhook",
            json={"update_id": 999},
        )
        assert r.status_code == 200


class TestPushSubscription:
    async def test_subscribe_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/push/subscribe", json={
            "endpoint": "https://fcm.googleapis.com/test/endpoint",
            "p256dh": "test_p256dh_key",
            "auth": "test_auth_key",
            "device_name": "Chrome on Android",
        })
        assert r.status_code == 201

    async def test_subscribe_has_required_fields(
        self, client: AsyncClient
    ) -> None:
        data = (
            await client.post("/api/v1/push/subscribe", json={
                "endpoint": "https://fcm.googleapis.com/test/endpoint2",
                "p256dh": "key2",
                "auth": "auth2",
            })
        ).json()
        assert "id" in data
        assert "endpoint" in data
        assert "created_at" in data
