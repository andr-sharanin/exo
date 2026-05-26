"""
E2E tests for Phase 9: Admin SystemConfig endpoints.
Tests require system_admin role to read/write config.
"""
import pytest
from httpx import AsyncClient


@pytest.fixture
def sysadmin_client(client: AsyncClient, monkeypatch):
    """Client with system_admin role."""
    from app.core.auth import TokenClaims
    import uuid

    claims = TokenClaims(
        sub="sysadmin",
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        roles=["user", "admin", "system_admin"],
    )

    async def _override():
        return claims

    from app.core.auth import get_current_user
    from app.core.database import get_db

    app = client.app
    app.dependency_overrides[get_current_user] = _override
    return client


class TestConfigRead:
    async def test_get_config_returns_200(
        self, sysadmin_client: AsyncClient
    ) -> None:
        r = await sysadmin_client.get("/api/v1/admin/config")
        assert r.status_code == 200

    async def test_get_config_returns_list(
        self, sysadmin_client: AsyncClient
    ) -> None:
        data = (await sysadmin_client.get("/api/v1/admin/config")).json()
        assert isinstance(data, list)

    async def test_non_sysadmin_cannot_read_config(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/admin/config")
        assert r.status_code == 403


class TestConfigWrite:
    async def test_set_non_secret_config(
        self, sysadmin_client: AsyncClient
    ) -> None:
        r = await sysadmin_client.put("/api/v1/admin/config/agent_prompt_coach", json={
            "value": "You are a coach. Be direct.",
            "is_secret": False,
            "description": "Coach agent system prompt",
            "category": "agent_prompts",
        })
        assert r.status_code == 200

    async def test_set_secret_config(
        self, sysadmin_client: AsyncClient
    ) -> None:
        r = await sysadmin_client.put("/api/v1/admin/config/anthropic_api_key", json={
            "value": "sk-ant-test-key",
            "is_secret": True,
            "description": "Anthropic API key",
            "category": "ai_keys",
        })
        assert r.status_code == 200

    async def test_secret_value_masked_in_get(
        self, sysadmin_client: AsyncClient
    ) -> None:
        await sysadmin_client.put("/api/v1/admin/config/openai_api_key", json={
            "value": "sk-openai-secret",
            "is_secret": True,
            "description": "OpenAI key",
            "category": "ai_keys",
        })
        data = (await sysadmin_client.get("/api/v1/admin/config")).json()
        openai_entry = next(
            (e for e in data if e["key"] == "openai_api_key"), None
        )
        assert openai_entry is not None
        assert openai_entry["value"] != "sk-openai-secret"
        assert "***" in openai_entry["value"] or openai_entry["value"] == ""

    async def test_set_and_get_single_key(
        self, sysadmin_client: AsyncClient
    ) -> None:
        await sysadmin_client.put("/api/v1/admin/config/telegram_bot_token", json={
            "value": "bot123:ABC",
            "is_secret": True,
            "description": "Telegram bot token",
            "category": "integrations",
        })
        r = await sysadmin_client.get("/api/v1/admin/config/telegram_bot_token")
        assert r.status_code == 200
        data = r.json()
        assert data["key"] == "telegram_bot_token"

    async def test_non_sysadmin_cannot_write_config(
        self, client: AsyncClient
    ) -> None:
        r = await client.put("/api/v1/admin/config/some_key", json={
            "value": "val", "is_secret": False,
            "description": "", "category": "misc",
        })
        assert r.status_code == 403
