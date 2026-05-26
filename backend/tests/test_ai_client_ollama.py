"""
Tests for AI client Ollama api_base fix.

Verifies that ollama/ model calls include api_base explicitly,
so LiteLLM routes to the local Ollama server rather than failing.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_client import AIClient
from app.services.ai_router import AITier, AITierConfig


def _make_config(primary_model: str, fallbacks: list[str] | None = None) -> AITierConfig:
    return AITierConfig(
        tier=AITier.MECHANICAL,
        primary_model=primary_model,
        fallback_models=fallbacks or [],
        max_tokens=64,
        temperature=0.1,
    )


def _fake_response(text: str = '{"ok": true}') -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    return resp


class TestOllamaApiBase:
    @pytest.mark.asyncio
    async def test_ollama_model_includes_api_base(self) -> None:
        """api_base must be passed to litellm.acompletion for ollama/ models."""
        captured: dict = {}

        async def _fake(**kwargs):
            captured.update(kwargs)
            return _fake_response()

        with (
            patch("litellm.acompletion", new=_fake),
            patch.dict(os.environ, {"OLLAMA_API_BASE": "http://ollama:11434"}),
        ):
            await AIClient.complete(
                messages=[{"role": "user", "content": "ping"}],
                config=_make_config("ollama/llama3"),
            )

        assert "api_base" in captured
        assert captured["api_base"] == "http://ollama:11434"

    @pytest.mark.asyncio
    async def test_ollama_api_base_defaults_to_localhost(self) -> None:
        """Falls back to localhost:11434 when OLLAMA_API_BASE is not set."""
        captured: dict = {}

        async def _fake(**kwargs):
            captured.update(kwargs)
            return _fake_response()

        env = {k: v for k, v in os.environ.items() if k != "OLLAMA_API_BASE"}
        with (
            patch("litellm.acompletion", new=_fake),
            patch.dict(os.environ, env, clear=True),
        ):
            await AIClient.complete(
                messages=[{"role": "user", "content": "ping"}],
                config=_make_config("ollama/llama3"),
            )

        assert captured.get("api_base") == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_non_ollama_model_does_not_receive_api_base(self) -> None:
        """Non-ollama models must NOT get api_base injected."""
        captured: dict = {}

        async def _fake(**kwargs):
            captured.update(kwargs)
            return _fake_response()

        with patch("litellm.acompletion", new=_fake):
            await AIClient.complete(
                messages=[{"role": "user", "content": "ping"}],
                config=_make_config("claude-haiku-4-5-20251001"),
            )

        assert "api_base" not in captured

    @pytest.mark.asyncio
    async def test_ollama_variant_model_gets_api_base(self) -> None:
        """Any ollama/* model string triggers api_base injection."""
        captured: dict = {}

        async def _fake(**kwargs):
            captured.update(kwargs)
            return _fake_response()

        with (
            patch("litellm.acompletion", new=_fake),
            patch.dict(os.environ, {"OLLAMA_API_BASE": "http://gpu:11434"}),
        ):
            await AIClient.complete(
                messages=[{"role": "user", "content": "ping"}],
                config=_make_config("ollama/mistral:7b"),
            )

        assert captured["api_base"] == "http://gpu:11434"
        assert captured["model"] == "ollama/mistral:7b"

    @pytest.mark.asyncio
    async def test_fallback_to_ollama_includes_api_base(self) -> None:
        """When primary fails and ollama fallback kicks in, api_base is still injected."""
        call_count = 0
        captured_second: dict = {}

        async def _fake(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("primary failed")
            captured_second.update(kwargs)
            return _fake_response()

        with (
            patch("litellm.acompletion", new=_fake),
            patch.dict(os.environ, {"OLLAMA_API_BASE": "http://local:11434"}),
        ):
            await AIClient.complete(
                messages=[{"role": "user", "content": "ping"}],
                config=_make_config(
                    "claude-haiku-4-5-20251001",
                    fallbacks=["ollama/llama3"],
                ),
            )

        assert call_count == 2
        assert captured_second.get("api_base") == "http://local:11434"
