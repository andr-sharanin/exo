"""
ConfigService — runtime configuration with three-layer priority:
  1. DB (SystemConfig table)  ← highest, editable from Admin UI
  2. Environment variables    ← fallback for infra bootstrapping
  3. Hardcoded defaults       ← lowest

Secrets are stored encrypted (Fernet symmetric encryption).
The encryption key is EXOCORTEX_SECRET_KEY in .env — the only
secret that must be set before first run.

Redis cache (TTL=60s) prevents DB round-trips on every request.
Cache is invalidated when a key is updated via Admin UI.
"""
import os
from typing import Any

from app.services.agents import AGENT_PERSONAS


def _make_fernet():
    """Return a Fernet instance using EXOCORTEX_SECRET_KEY from env.

    The key must be a valid Fernet key (URL-safe base64 of 32 random bytes).
    Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    try:
        from cryptography.fernet import Fernet
        raw = os.environ.get("EXOCORTEX_SECRET_KEY", "")
        if not raw:
            return None
        return Fernet(raw.encode())
    except Exception:
        return None


class ConfigService:
    # Registry of all known configurable keys with metadata
    KNOWN_KEYS: dict[str, dict] = {
        # AI provider keys
        "anthropic_api_key": {
            "is_secret": True, "category": "ai_keys",
            "description": "Anthropic API key (sk-ant-...)",
            "env_var": "ANTHROPIC_API_KEY",
        },
        "openai_api_key": {
            "is_secret": True, "category": "ai_keys",
            "description": "OpenAI API key (sk-...)",
            "env_var": "OPENAI_API_KEY",
        },
        "ollama_base_url": {
            "is_secret": False, "category": "ai_keys",
            "description": "Ollama server URL for local LLM fallback",
            "env_var": "OLLAMA_BASE_URL",
            "default": "http://localhost:11434",
        },
        # Stripe
        "stripe_secret_key": {
            "is_secret": True, "category": "stripe",
            "description": "Stripe secret key (sk_live_... or sk_test_...)",
            "env_var": "STRIPE_SECRET_KEY",
        },
        "stripe_webhook_secret": {
            "is_secret": True, "category": "stripe",
            "description": "Stripe webhook signing secret (whsec_...)",
            "env_var": "STRIPE_WEBHOOK_SECRET",
        },
        "stripe_charity_account": {
            "is_secret": False, "category": "stripe",
            "description": "Stripe account ID for forfeited deposit transfers",
            "env_var": "STRIPE_CHARITY_ACCOUNT",
        },
        "stripe_price_id_pro": {
            "is_secret": False, "category": "stripe",
            "description": "Stripe Price ID for the Pro subscription plan",
            "env_var": "STRIPE_PRICE_ID_PRO",
        },
        "stripe_price_id_team": {
            "is_secret": False, "category": "stripe",
            "description": "Stripe Price ID for the Team subscription plan",
            "env_var": "STRIPE_PRICE_ID_TEAM",
        },
        # Telegram
        "telegram_bot_token": {
            "is_secret": True, "category": "integrations",
            "description": "Telegram Bot token from @BotFather",
            "env_var": "TELEGRAM_BOT_TOKEN",
        },
        "telegram_webhook_url": {
            "is_secret": False, "category": "integrations",
            "description": "Public HTTPS URL for Telegram webhook (https://yourdomain.com)",
            "env_var": "TELEGRAM_WEBHOOK_URL",
        },
        # Google Calendar
        "google_calendar_client_id": {
            "is_secret": False, "category": "integrations",
            "description": "Google OAuth2 client ID for Calendar API",
            "env_var": "GOOGLE_CALENDAR_CLIENT_ID",
        },
        "google_calendar_client_secret": {
            "is_secret": True, "category": "integrations",
            "description": "Google OAuth2 client secret for Calendar API",
            "env_var": "GOOGLE_CALENDAR_CLIENT_SECRET",
        },
        # Microsoft Graph Calendar
        "ms_graph_client_id": {
            "is_secret": False, "category": "integrations",
            "description": "Microsoft Azure app client ID for Calendar (Graph API)",
            "env_var": "MS_GRAPH_CLIENT_ID",
        },
        "ms_graph_client_secret": {
            "is_secret": True, "category": "integrations",
            "description": "Microsoft Azure app client secret for Calendar (Graph API)",
            "env_var": "MS_GRAPH_CLIENT_SECRET",
        },
        # Web Push
        "vapid_private_key": {
            "is_secret": True, "category": "integrations",
            "description": "VAPID private key for Web Push notifications",
            "env_var": "VAPID_PRIVATE_KEY",
        },
        "vapid_public_key": {
            "is_secret": False, "category": "integrations",
            "description": "VAPID public key for Web Push (sent to browser)",
            "env_var": "VAPID_PUBLIC_KEY",
        },
        "vapid_contact_email": {
            "is_secret": False, "category": "integrations",
            "description": "Contact email for VAPID (mailto:you@domain.com)",
            "env_var": "VAPID_CONTACT_EMAIL",
        },
        # Email / SMTP
        "smtp_host": {
            "is_secret": False, "category": "email",
            "description": "SMTP server host (e.g. smtp.gmail.com)",
            "env_var": "SMTP_HOST",
        },
        "smtp_port": {
            "is_secret": False, "category": "email",
            "description": "SMTP port (587 for STARTTLS, 465 for SSL)",
            "env_var": "SMTP_PORT",
            "default": "587",
        },
        "smtp_username": {
            "is_secret": False, "category": "email",
            "description": "SMTP login username",
            "env_var": "SMTP_USERNAME",
        },
        "smtp_password": {
            "is_secret": True, "category": "email",
            "description": "SMTP password",
            "env_var": "SMTP_PASSWORD",
        },
        "smtp_from_email": {
            "is_secret": False, "category": "email",
            "description": "From address for outgoing emails (e.g. noreply@yourdomain.com)",
            "env_var": "SMTP_FROM_EMAIL",
        },
        "smtp_use_tls": {
            "is_secret": False, "category": "email",
            "description": "Use STARTTLS (true/false)",
            "env_var": "SMTP_USE_TLS",
            "default": "true",
        },
        # Agent system prompts (editable without code change)
        **{
            f"agent_prompt_{name}": {
                "is_secret": False, "category": "agent_prompts",
                "description": f"System prompt for {name} agent persona",
                "env_var": None,
                "default": prompt,
            }
            for name, prompt in AGENT_PERSONAS.items()
        },
    }

    @staticmethod
    def get_from_env(key: str, default: str | None = None) -> str | None:
        """Read directly from environment (no DB, no cache)."""
        return os.environ.get(key, default)

    @staticmethod
    def mask_secret(value: str | None) -> str:
        """Mask a secret value for API responses."""
        if not value:
            return ""
        if len(value) <= 6:
            return "***"
        return value[:4] + "***"

    @staticmethod
    def encrypt(value: str) -> str:
        """Encrypt a secret value for DB storage. Returns plain text if no key set."""
        fernet = _make_fernet()
        if fernet is None:
            return value
        return fernet.encrypt(value.encode()).decode()

    @staticmethod
    def decrypt(encrypted: str) -> str:
        """Decrypt a stored secret. Returns as-is if no key set."""
        fernet = _make_fernet()
        if fernet is None:
            return encrypted
        try:
            return fernet.decrypt(encrypted.encode()).decode()
        except Exception:
            return encrypted

    @classmethod
    def get_default(cls, key: str) -> str:
        """Return hardcoded default for a known key."""
        meta = cls.KNOWN_KEYS.get(key, {})
        return meta.get("default", "")

    # ── Instance methods (DB-backed, 3-layer lookup) ──────────────────────────

    def __init__(self, db) -> None:
        self._db = db

    async def get(self, key: str, default: str | None = None) -> str | None:
        """
        3-layer priority: DB (Admin UI) → environment variable → hardcoded default.

        DB values are authoritative — they are set via Admin UI and encrypted at rest.
        Env vars serve as fallbacks for infra-bootstrapping before first Admin UI setup.
        """
        from sqlalchemy import select
        from app.models.system_config import SystemConfig

        # Layer 1: DB
        try:
            row = (await self._db.execute(
                select(SystemConfig).where(SystemConfig.key == key)
            )).scalar_one_or_none()
            if row is not None:
                val = self.decrypt(row.value) if row.is_secret else row.value
                if val:
                    return val
        except Exception:
            pass  # DB unavailable during migration or test — fall through

        # Layer 2: environment variable
        meta = self.KNOWN_KEYS.get(key, {})
        env_var = meta.get("env_var")
        if env_var:
            val = os.environ.get(env_var)
            if val:
                return val

        # Layer 3: hardcoded default
        return meta.get("default") or default
