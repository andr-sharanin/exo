"""
Unit tests for Phase 9: ConfigService.
Tests env fallback and default behavior without DB.
"""
import os
import pytest

from app.services.config_service import ConfigService


class TestEnvFallback:
    def test_returns_env_value_when_set(self, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
        assert ConfigService.get_from_env("ANTHROPIC_API_KEY") == "sk-from-env"

    def test_returns_default_when_env_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert ConfigService.get_from_env("ANTHROPIC_API_KEY", default="fallback") == "fallback"

    def test_returns_none_when_no_env_no_default(self, monkeypatch) -> None:
        monkeypatch.delenv("NONEXISTENT_KEY_XYZ", raising=False)
        assert ConfigService.get_from_env("NONEXISTENT_KEY_XYZ") is None


class TestSecretMasking:
    def test_mask_short_secret(self) -> None:
        assert ConfigService.mask_secret("abc") == "***"

    def test_mask_long_secret_shows_prefix(self) -> None:
        masked = ConfigService.mask_secret("sk-ant-api-key-very-long")
        assert masked.endswith("***")
        assert len(masked) < len("sk-ant-api-key-very-long")

    def test_mask_empty_string(self) -> None:
        assert ConfigService.mask_secret("") == ""

    def test_mask_none(self) -> None:
        assert ConfigService.mask_secret(None) == ""


class TestKnownKeys:
    def test_known_config_keys_defined(self) -> None:
        assert len(ConfigService.KNOWN_KEYS) > 0

    def test_anthropic_key_in_known_keys(self) -> None:
        assert "anthropic_api_key" in ConfigService.KNOWN_KEYS

    def test_agent_prompts_in_known_keys(self) -> None:
        assert "agent_prompt_core_advisor" in ConfigService.KNOWN_KEYS
        assert "agent_prompt_coach" in ConfigService.KNOWN_KEYS

    def test_stripe_key_in_known_keys(self) -> None:
        assert "stripe_secret_key" in ConfigService.KNOWN_KEYS

    def test_telegram_token_in_known_keys(self) -> None:
        assert "telegram_bot_token" in ConfigService.KNOWN_KEYS
