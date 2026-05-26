"""
AgentService — persona-driven AI advisor entities.

Phase 16: Dynamic personas from DB (agent_personas table).
Falls back to hardcoded defaults if no DB persona found.

Each persona has its own kernel:
  - system_prompt: base instruction
  - training_context: admin-accumulated knowledge
  - knowledge_base: documents injected into every conversation
  - behavior_rules: specific constraints
  - tone_style: language/format settings
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_client import AIClient, AIResponse
from app.services.ai_router import AIRoutingContext, AIRouter, PipelineStage

# ── Default kernels (used when no DB persona exists or for seeding) ───────────

_DEFAULT_PERSONAS: dict[str, dict] = {
    "core_advisor": {
        "display_name": "Core Advisor",
        "avatar_emoji": "🧠",
        "description": "Strategic inner voice. Prioritize, decide, maintain clarity.",
        "system_prompt": (
            "You are the Core Advisor — the user's strategic inner voice. "
            "Help prioritize, decide, and maintain clarity under pressure. "
            "Be concise, direct, and solution-oriented."
        ),
        "preferred_tier": 2,
    },
    "tutor": {
        "display_name": "Tutor",
        "avatar_emoji": "📚",
        "description": "Patient, educational, Socratic. Deep understanding through guided discovery.",
        "system_prompt": (
            "You are the Tutor — patient, educational, and Socratic. "
            "Help the user understand concepts deeply through guided discovery."
        ),
        "preferred_tier": 2,
    },
    "reflective_support": {
        "display_name": "Reflective Support",
        "avatar_emoji": "💭",
        "description": "Empathetic. Help process emotions and discover behavioral patterns.",
        "system_prompt": (
            "You are the Reflective Support entity — empathetic and insight-driven. "
            "Help the user process emotions and discover behavioral patterns."
        ),
        "preferred_tier": 2,
    },
    "coach": {
        "display_name": "Coach",
        "avatar_emoji": "⚡",
        "description": "Motivating, results-focused, accountability-driven.",
        "system_prompt": (
            "You are the Coach — motivating, results-focused, and accountability-driven. "
            "Push toward action while acknowledging feelings."
        ),
        "preferred_tier": 2,
    },
    "consultant": {
        "display_name": "Consultant",
        "avatar_emoji": "📊",
        "description": "Analytical, evidence-based, structured frameworks.",
        "system_prompt": (
            "You are the Consultant — analytical, evidence-based, and structured. "
            "Provide frameworks and clear recommendations with supporting rationale."
        ),
        "preferred_tier": 2,
    },
}

# Kept for schema validation fallback (updated dynamically from DB)
DEFAULT_ENTITY_TYPES = frozenset(_DEFAULT_PERSONAS.keys())

_JSON_SUFFIX = '\nRespond in valid JSON: {"response": str, "action_items": list[str], "confidence": float}'


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_persona(self, entity_type: str, tenant_id: str) -> dict:
        """
        Load persona from DB (tenant-scoped).
        Falls back to hardcoded defaults if not found.
        """
        from app.models.agent_persona import AgentPersona
        q = (
            select(AgentPersona)
            .where(
                AgentPersona.tenant_id == tenant_id,
                AgentPersona.entity_type == entity_type,
                AgentPersona.is_enabled == True,  # noqa: E712
            )
            .limit(1)
        )
        persona = (await self.db.execute(q)).scalar_one_or_none()

        if persona:
            return {
                "system_prompt": persona.system_prompt or "",
                "training_context": persona.training_context or "",
                "knowledge_base": persona.knowledge_base or [],
                "behavior_rules": persona.behavior_rules or [],
                "tone_style": persona.tone_style or {},
                "preferred_tier": persona.preferred_tier,
                "preferred_model": persona.preferred_model,
                "display_name": persona.display_name,
                "avatar_emoji": persona.avatar_emoji,
            }

        # Fallback to hardcoded defaults
        default = _DEFAULT_PERSONAS.get(entity_type)
        if not default:
            raise ValueError(f"Unknown entity_type: {entity_type}")
        return default

    async def is_valid_entity_type(self, entity_type: str, tenant_id: str) -> bool:
        """Check if entity_type exists for this tenant (DB or default)."""
        from app.models.agent_persona import AgentPersona
        q = select(AgentPersona).where(
            AgentPersona.tenant_id == tenant_id,
            AgentPersona.entity_type == entity_type,
            AgentPersona.is_enabled == True,  # noqa: E712
        )
        db_exists = (await self.db.execute(q)).scalar_one_or_none() is not None
        return db_exists or entity_type in DEFAULT_ENTITY_TYPES

    def build_system_prompt(self, persona: dict) -> str:
        """Assemble full system prompt from persona kernel components."""
        parts = [persona.get("system_prompt", "")]

        if persona.get("training_context"):
            parts.append(
                f"\n\nADDITIONAL KNOWLEDGE (from training):\n{persona['training_context']}"
            )

        kb = persona.get("knowledge_base") or []
        if kb:
            kb_text = "\n".join(
                f"[{item.get('title', 'Document')}]\n{item.get('content', '')}"
                for item in kb[:5]  # Max 5 documents to stay within context
            )
            parts.append(f"\n\nKNOWLEDGE BASE:\n{kb_text}")

        rules = persona.get("behavior_rules") or []
        if rules:
            rules_text = "\n".join(f"- {r}" for r in rules)
            parts.append(f"\n\nBEHAVIOR RULES:\n{rules_text}")

        tone = persona.get("tone_style") or {}
        if tone:
            tone_lines = []
            if tone.get("language"):
                tone_lines.append(f"Language register: {tone['language']}")
            if tone.get("response_length"):
                tone_lines.append(f"Response length: {tone['response_length']}")
            if tone.get("format"):
                tone_lines.append(f"Response format: {tone['format']}")
            if tone_lines:
                parts.append("\n\nTONE:\n" + "\n".join(tone_lines))

        parts.append(_JSON_SUFFIX)
        return "".join(parts)

    def build_messages(
        self,
        persona: dict,
        history: list[dict],
        user_content: str,
        task_context: dict | None = None,
    ) -> list[dict]:
        system = self.build_system_prompt(persona)
        messages = [{"role": "system", "content": system}]

        # Inject task context if provided (for LifeWorm in-task calls)
        if task_context:
            ctx_text = (
                f"[CURRENT TASK CONTEXT]\n"
                f"Task: {task_context.get('title', 'unknown')}\n"
                f"Progress: {task_context.get('progress_pct', 0)}%\n"
                f"Time elapsed: {task_context.get('elapsed_minutes', 0)} min\n"
                f"Estimated total: {task_context.get('estimated_minutes', 0)} min\n"
                f"Notes: {task_context.get('notes', '')}"
            )
            messages.append({"role": "system", "content": ctx_text})

        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def chat(
        self,
        entity_type: str,
        tenant_id: str,
        history: list[dict],
        user_content: str,
        task_context: dict | None = None,
    ) -> AIResponse:
        persona = await self.get_persona(entity_type, tenant_id)

        context = AIRoutingContext(
            stage=PipelineStage.ADVISORY,
            complexity="high",
            energy_state="sufficient",
        )
        config = AIRouter.route(context)

        # Override tier/model if persona specifies
        if persona.get("preferred_tier"):
            config.tier = persona["preferred_tier"]  # type: ignore[attr-defined]
        if persona.get("preferred_model"):
            config.primary_model = persona["preferred_model"]  # type: ignore[attr-defined]

        messages = self.build_messages(persona, history, user_content, task_context)
        return await AIClient.complete(messages, config)

    async def append_training(
        self,
        entity_type: str,
        tenant_id: str,
        new_context: str,
    ) -> None:
        """Admin trains an agent by appending to its training_context."""
        from app.models.agent_persona import AgentPersona
        from sqlalchemy import update
        q = (
            select(AgentPersona)
            .where(
                AgentPersona.tenant_id == tenant_id,
                AgentPersona.entity_type == entity_type,
            )
            .limit(1)
        )
        persona = (await self.db.execute(q)).scalar_one_or_none()
        if not persona:
            raise ValueError(f"Persona {entity_type} not found for tenant")

        separator = "\n\n---\n\n"
        existing = persona.training_context or ""
        persona.training_context = (existing + separator + new_context).strip()

        from datetime import datetime, timezone
        persona.last_trained_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def list_for_tenant(self, tenant_id: str) -> list[dict]:
        """Return all enabled personas for a tenant (DB + defaults not yet in DB)."""
        from app.models.agent_persona import AgentPersona
        q = select(AgentPersona).where(
            AgentPersona.tenant_id == tenant_id,
        ).order_by(AgentPersona.is_default.desc(), AgentPersona.created_at)
        db_personas = list((await self.db.execute(q)).scalars().all())
        db_types = {p.entity_type for p in db_personas}

        result = [
            {
                "id": str(p.id),
                "entity_type": p.entity_type,
                "display_name": p.display_name,
                "avatar_emoji": p.avatar_emoji,
                "description": p.description,
                "is_enabled": p.is_enabled,
                "is_default": p.is_default,
                "preferred_tier": p.preferred_tier,
                "total_conversations": p.total_conversations,
                "has_training": bool(p.training_context),
                "has_knowledge_base": bool(p.knowledge_base),
            }
            for p in db_personas
        ]

        # Add hardcoded defaults not yet in DB (will be seeded on first use)
        for entity_type, defaults in _DEFAULT_PERSONAS.items():
            if entity_type not in db_types:
                result.append({
                    "id": None,
                    "entity_type": entity_type,
                    "display_name": defaults["display_name"],
                    "avatar_emoji": defaults["avatar_emoji"],
                    "description": defaults.get("description"),
                    "is_enabled": True,
                    "is_default": True,
                    "preferred_tier": defaults.get("preferred_tier", 2),
                    "total_conversations": 0,
                    "has_training": False,
                    "has_knowledge_base": False,
                })

        return result
