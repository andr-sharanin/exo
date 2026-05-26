"""
E2E tests for Phase 7: /agents/* endpoints.
AI responses are mocked via monkeypatch.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


def _ai_mock(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = 30
    resp.usage.completion_tokens = 60
    return resp


_AGENT_REPLY = json.dumps({
    "response": "Focus on your most impactful task first.",
    "action_items": ["Block 45 minutes", "Silence notifications"],
    "confidence": 0.88,
})


class TestAgentSession:
    async def test_create_session_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/agents/sessions", json={
            "entity_type": "core_advisor",
            "session_mode": "advisory",
        })
        assert r.status_code == 201

    async def test_create_session_response_has_required_fields(
        self, client: AsyncClient
    ) -> None:
        data = (
            await client.post("/api/v1/agents/sessions", json={
                "entity_type": "core_advisor",
                "session_mode": "advisory",
            })
        ).json()
        assert "id" in data
        assert "entity_type" in data
        assert "session_mode" in data
        assert "status" in data
        assert data["status"] == "active"
        assert data["entity_type"] == "core_advisor"

    async def test_all_five_entity_types_accepted(
        self, client: AsyncClient
    ) -> None:
        entity_types = [
            "core_advisor", "tutor", "reflective_support", "coach", "consultant"
        ]
        for et in entity_types:
            r = await client.post("/api/v1/agents/sessions", json={
                "entity_type": et, "session_mode": "advisory",
            })
            assert r.status_code == 201, f"entity_type {et!r} was rejected"

    async def test_invalid_entity_type_returns_422(
        self, client: AsyncClient
    ) -> None:
        r = await client.post("/api/v1/agents/sessions", json={
            "entity_type": "gpt_overlord", "session_mode": "advisory",
        })
        assert r.status_code == 422


class TestAgentMessage:
    async def test_send_message_returns_201(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion", AsyncMock(return_value=_ai_mock(_AGENT_REPLY))
        )
        session_id = (
            await client.post("/api/v1/agents/sessions", json={
                "entity_type": "core_advisor", "session_mode": "advisory",
            })
        ).json()["id"]
        r = await client.post(
            f"/api/v1/agents/sessions/{session_id}/message",
            json={"content": "How should I start my day?"},
        )
        assert r.status_code == 201

    async def test_send_message_returns_assistant_reply(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion", AsyncMock(return_value=_ai_mock(_AGENT_REPLY))
        )
        session_id = (
            await client.post("/api/v1/agents/sessions", json={
                "entity_type": "coach", "session_mode": "advisory",
            })
        ).json()["id"]
        data = (
            await client.post(
                f"/api/v1/agents/sessions/{session_id}/message",
                json={"content": "Motivate me!"},
            )
        ).json()
        assert "content" in data
        assert "role" in data
        assert data["role"] == "assistant"
        assert "model_used" in data

    async def test_get_messages_returns_history(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion", AsyncMock(return_value=_ai_mock(_AGENT_REPLY))
        )
        session_id = (
            await client.post("/api/v1/agents/sessions", json={
                "entity_type": "tutor", "session_mode": "reflection",
            })
        ).json()["id"]
        await client.post(
            f"/api/v1/agents/sessions/{session_id}/message",
            json={"content": "Explain focus."},
        )
        r = await client.get(f"/api/v1/agents/sessions/{session_id}/messages")
        assert r.status_code == 200
        messages = r.json()
        # user message + assistant reply = 2
        assert len(messages) == 2

    async def test_send_message_to_unknown_session_returns_404(
        self, client: AsyncClient
    ) -> None:
        import uuid
        r = await client.post(
            f"/api/v1/agents/sessions/{uuid.uuid4()}/message",
            json={"content": "Hello?"},
        )
        assert r.status_code == 404
