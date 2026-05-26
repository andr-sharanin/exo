"""
E2E tests for Phase 6: /ai/* endpoints.
LiteLLM is mocked — no real API calls.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


def _litellm_mock(content: str, model: str = "claude-haiku-4-5-20251001") -> MagicMock:
    """Build a fake litellm.acompletion return value."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = 45
    resp.usage.completion_tokens = 28
    return resp


_CLASSIFY_JSON = json.dumps({
    "intent_class": "task",
    "urgency": "medium",
    "complexity": "low",
    "confidence": 0.92,
})

_REASON_JSON = json.dumps({
    "intent_hypothesis": "Write a Q2 report for stakeholders",
    "ambiguity_level": "low",
    "actionability_status": "actionable",
    "reasoning": "Clear deliverable with an implicit deadline.",
})

_ADVISORY_JSON = json.dumps({
    "response": "Focus on the single highest-impact item first.",
    "suggestions": ["Block 45 min", "Turn off notifications", "Draft outline first"],
    "confidence": 0.87,
})


class TestClassify:
    async def test_classify_returns_201(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_CLASSIFY_JSON)),
        )
        r = await client.post(
            "/api/v1/ai/classify", json={"text": "Write the Q2 report"}
        )
        assert r.status_code == 201

    async def test_classify_response_has_required_fields(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_CLASSIFY_JSON)),
        )
        data = (
            await client.post(
                "/api/v1/ai/classify", json={"text": "Write the Q2 report"}
            )
        ).json()
        assert "request_id" in data
        assert "tier" in data
        assert "model_used" in data
        assert "intent_class" in data
        assert "urgency" in data
        assert "complexity" in data
        assert "confidence" in data
        assert "prompt_tokens" in data
        assert "latency_ms" in data

    async def test_classify_uses_mechanical_tier(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_CLASSIFY_JSON)),
        )
        data = (
            await client.post(
                "/api/v1/ai/classify", json={"text": "Anything"}
            )
        ).json()
        assert data["tier"] == "mechanical"

    async def test_classify_missing_text_returns_422(
        self, client: AsyncClient
    ) -> None:
        r = await client.post("/api/v1/ai/classify", json={})
        assert r.status_code == 422


class TestReason:
    async def test_reason_returns_201(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_REASON_JSON)),
        )
        r = await client.post("/api/v1/ai/reason", json={
            "text": "Write Q2 report", "intent_class": "task", "complexity": "medium",
        })
        assert r.status_code == 201

    async def test_reason_response_has_required_fields(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_REASON_JSON)),
        )
        data = (
            await client.post("/api/v1/ai/reason", json={
                "text": "Write Q2 report", "intent_class": "task", "complexity": "medium",
            })
        ).json()
        assert "intent_hypothesis" in data
        assert "ambiguity_level" in data
        assert "actionability_status" in data
        assert "reasoning" in data
        assert "tier" in data

    async def test_high_complexity_sufficient_energy_uses_strategic(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_REASON_JSON)),
        )
        data = (
            await client.post("/api/v1/ai/reason", json={
                "text": "Complex architecture decision",
                "intent_class": "task",
                "complexity": "high",
                "energy_state": "sufficient",
            })
        ).json()
        assert data["tier"] == "strategic"

    async def test_critical_energy_forces_mechanical(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_REASON_JSON)),
        )
        data = (
            await client.post("/api/v1/ai/reason", json={
                "text": "Anything",
                "intent_class": "task",
                "complexity": "high",
                "energy_state": "critical",
            })
        ).json()
        assert data["tier"] == "mechanical"


class TestAdvisory:
    async def test_advisory_returns_201(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_ADVISORY_JSON)),
        )
        r = await client.post(
            "/api/v1/ai/advisory",
            json={"query": "How should I approach my day?"},
        )
        assert r.status_code == 201

    async def test_advisory_response_has_required_fields(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_ADVISORY_JSON)),
        )
        data = (
            await client.post(
                "/api/v1/ai/advisory",
                json={"query": "What should I focus on?"},
            )
        ).json()
        assert "response" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert "confidence" in data
        assert "tier" in data

    async def test_advisory_uses_analytical_tier(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=_litellm_mock(_ADVISORY_JSON)),
        )
        data = (
            await client.post(
                "/api/v1/ai/advisory",
                json={"query": "What to work on?", "energy_state": "sufficient"},
            )
        ).json()
        assert data["tier"] == "analytical"
