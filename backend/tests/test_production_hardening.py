# TDD RED — Production hardening checks. Written before alembic/0008 migration.
import pytest
from sqlalchemy import text
from app.services.config_service import ConfigService

# Tables that MUST have RLS enabled and forced.
# system_configs is intentionally excluded — admin-only via API layer.
TENANT_SCOPED_TABLES = [
    "commands",
    "capture_records",
    "reasoning_artifacts",
    "decision_objects",
    "schedule_objects",
    "step_objects",
    "execution_sessions",
    "witness_objects",
    "outcome_objects",
    "entity_sessions",
    "memory_objects",
    "behavioral_events",
    "energy_scores",
    "system_modes",
    "client_kernel_profiles",
    "onboarding_sessions",
    "ai_request_logs",
    "day_plans",
    "agent_messages",
    "planning_goals",
    "commitment_deposits",
    "push_subscriptions",
]

VALID_CATEGORIES = {"ai_keys", "agent_prompts", "integrations", "stripe", "misc"}


# ── Config service unit tests (no DB) ─────────────────────────────────────────

def test_all_known_config_keys_have_required_fields():
    for key, meta in ConfigService.KNOWN_KEYS.items():
        assert "description" in meta, f"KNOWN_KEYS[{key!r}] missing 'description'"
        assert "category" in meta, f"KNOWN_KEYS[{key!r}] missing 'category'"
        assert "is_secret" in meta, f"KNOWN_KEYS[{key!r}] missing 'is_secret'"
        assert meta["category"] in VALID_CATEGORIES, (
            f"KNOWN_KEYS[{key!r}] unknown category: {meta['category']!r}"
        )


def test_ai_keys_are_marked_secret():
    ai_key_names = [k for k, m in ConfigService.KNOWN_KEYS.items() if m["category"] == "ai_keys"]
    assert len(ai_key_names) >= 2, "Expected at least anthropic_api_key and openai_api_key"
    for k in ai_key_names:
        assert ConfigService.KNOWN_KEYS[k]["is_secret"] is True, f"{k!r} must be secret"


def test_agent_prompts_are_not_secret():
    prompt_keys = [k for k, m in ConfigService.KNOWN_KEYS.items() if m["category"] == "agent_prompts"]
    assert len(prompt_keys) >= 1, "Expected at least one agent prompt key"
    for k in prompt_keys:
        assert ConfigService.KNOWN_KEYS[k]["is_secret"] is False, f"{k!r} prompts should not be secret"


def test_mask_secret_hides_key():
    masked = ConfigService.mask_secret("sk-ant-abc123fullkey")
    assert "sk-a" in masked
    assert "abc123fullkey" not in masked
    assert "***" in masked


def test_mask_secret_handles_short_value():
    # Values shorter than 4 chars should still mask
    masked = ConfigService.mask_secret("ab")
    assert "***" in masked


# ── Database-level RLS tests (require live DB via conftest) ───────────────────

@pytest.mark.asyncio
async def test_rls_enabled_on_all_tenant_tables(db):
    """Every tenant-scoped table must have RLS enabled (relrowsecurity = true)."""
    for table in TENANT_SCOPED_TABLES:
        result = await db.execute(
            text("SELECT relrowsecurity FROM pg_class WHERE relname = :t AND relkind = 'r'"),
            {"t": table},
        )
        row = result.fetchone()
        assert row is not None, f"Table '{table}' not found in pg_class"
        assert row[0] is True, f"RLS not ENABLED on table '{table}'"


@pytest.mark.asyncio
async def test_rls_forced_on_all_tenant_tables(db):
    """FORCE ROW LEVEL SECURITY must be set so even the table owner goes through RLS."""
    for table in TENANT_SCOPED_TABLES:
        result = await db.execute(
            text("SELECT relforcerowsecurity FROM pg_class WHERE relname = :t AND relkind = 'r'"),
            {"t": table},
        )
        row = result.fetchone()
        assert row is not None, f"Table '{table}' not found in pg_class"
        assert row[0] is True, f"FORCE RLS not set on table '{table}' — run alembic upgrade head"


@pytest.mark.asyncio
async def test_system_configs_has_no_rls(db):
    """system_configs is intentionally RLS-free — access enforced at API layer (system_admin role)."""
    result = await db.execute(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'system_configs' AND relkind = 'r'"),
    )
    row = result.fetchone()
    assert row is not None, "system_configs table not found"
    assert row[0] is False, "system_configs should NOT have RLS (access controlled at API layer)"


@pytest.mark.asyncio
async def test_audit_log_has_no_forced_rls(db):
    """audit_log has RLS enabled but NOT forced — table owner (admin) needs cross-tenant reads."""
    result = await db.execute(
        text(
            "SELECT relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE relname = 'audit_log' AND relkind = 'r'"
        ),
    )
    row = result.fetchone()
    assert row is not None, "audit_log table not found"
    # RLS may or may not be enabled on audit_log, but FORCE must not be set
    assert row[1] is False, "audit_log must NOT have FORCE RLS"


@pytest.mark.asyncio
async def test_update_updated_at_trigger_exists_on_core_tables(db):
    """update_updated_at() trigger must exist on tables with updated_at column."""
    tables_with_trigger = ["commands", "step_objects", "planning_goals", "day_plans"]
    for table in tables_with_trigger:
        result = await db.execute(
            text(
                "SELECT count(*) FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "WHERE c.relname = :t AND t.tgname LIKE 'trg_updated_at_%'"
            ),
            {"t": table},
        )
        count = result.scalar()
        assert count and count >= 1, f"update_updated_at trigger missing on '{table}'"
