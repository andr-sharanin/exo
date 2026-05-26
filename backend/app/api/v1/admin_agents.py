"""
Admin API — dynamic agent persona management.

Tenant admins can: list, create, update, enable/disable, train, add knowledge.
system_admin can manage across all tenants.

GET    /admin/agents                        — list all personas for tenant
POST   /admin/agents                        — create new persona
GET    /admin/agents/{entity_type}          — get persona detail (with kernel)
PUT    /admin/agents/{entity_type}          — update persona (prompt, tone, rules)
DELETE /admin/agents/{entity_type}          — disable persona (soft delete)
POST   /admin/agents/{entity_type}/train    — append to training_context
POST   /admin/agents/{entity_type}/knowledge — add knowledge base document
DELETE /admin/agents/{entity_type}/knowledge/{idx} — remove KB document
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.agent_persona import AgentPersona
from app.services.agents import AgentService, _DEFAULT_PERSONAS

router = APIRouter(prefix="/admin/agents", tags=["admin", "agents"])


class PersonaCreate(BaseModel):
    name: str
    display_name: str
    entity_type: str
    avatar_emoji: str = "🤖"
    description: str | None = None
    system_prompt: str | None = None
    behavior_rules: list[str] | None = None
    tone_style: dict | None = None
    preferred_tier: int = 2
    preferred_model: str | None = None


class PersonaUpdate(BaseModel):
    display_name: str | None = None
    avatar_emoji: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    behavior_rules: list[str] | None = None
    tone_style: dict | None = None
    preferred_tier: int | None = None
    preferred_model: str | None = None
    is_enabled: bool | None = None


class TrainRequest(BaseModel):
    context: str


class KnowledgeItem(BaseModel):
    title: str
    content: str


def _require_admin(user: CurrentUser) -> None:
    if "admin" not in user.roles and "system_admin" not in user.roles:
        raise HTTPException(403, "Admin role required")


@router.get("")
async def list_personas(db: TenantDB, user: CurrentUser) -> list[dict]:
    svc = AgentService(db)
    return await svc.list_for_tenant(str(user.tenant_id))


@router.post("", status_code=201)
async def create_persona(
    body: PersonaCreate, db: TenantDB, user: CurrentUser
) -> dict:
    _require_admin(user)

    # Check uniqueness within tenant
    existing_q = select(AgentPersona).where(
        AgentPersona.tenant_id == user.tenant_id,
        AgentPersona.entity_type == body.entity_type,
    )
    if (await db.execute(existing_q)).scalar_one_or_none():
        raise HTTPException(409, f"entity_type '{body.entity_type}' already exists for this tenant")

    persona = AgentPersona(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        name=body.name,
        display_name=body.display_name,
        entity_type=body.entity_type,
        avatar_emoji=body.avatar_emoji,
        description=body.description,
        system_prompt=body.system_prompt,
        behavior_rules=body.behavior_rules,
        tone_style=body.tone_style,
        preferred_tier=body.preferred_tier,
        preferred_model=body.preferred_model,
        is_default=False,
        is_enabled=True,
    )
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    await db.commit()
    return _persona_detail(persona)


@router.get("/{entity_type}")
async def get_persona(entity_type: str, db: TenantDB, user: CurrentUser) -> dict:
    persona = await _get_or_404(entity_type, user.tenant_id, db)
    return _persona_detail(persona)


@router.put("/{entity_type}")
async def update_persona(
    entity_type: str, body: PersonaUpdate, db: TenantDB, user: CurrentUser
) -> dict:
    _require_admin(user)
    persona = await _get_or_seed(entity_type, user.tenant_id, user.user_id, db)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(persona, field, value)
    await db.flush()
    await db.commit()
    return _persona_detail(persona)


@router.delete("/{entity_type}", status_code=204)
async def disable_persona(entity_type: str, db: TenantDB, user: CurrentUser) -> None:
    _require_admin(user)
    persona = await _get_or_404(entity_type, user.tenant_id, db)
    if persona.is_default:
        raise HTTPException(400, "Cannot disable default personas")
    persona.is_enabled = False
    await db.flush()
    await db.commit()


@router.post("/{entity_type}/train")
async def train_persona(
    entity_type: str, body: TrainRequest, db: TenantDB, user: CurrentUser
) -> dict:
    """Admin appends training context to the agent's kernel."""
    _require_admin(user)
    persona = await _get_or_seed(entity_type, user.tenant_id, user.user_id, db)
    svc = AgentService(db)
    await svc.append_training(entity_type, str(user.tenant_id), body.context)
    await db.commit()
    await db.refresh(persona)
    return {
        "entity_type": entity_type,
        "training_context_length": len(persona.training_context or ""),
        "last_trained_at": persona.last_trained_at.isoformat() if persona.last_trained_at else None,
    }


@router.post("/{entity_type}/knowledge", status_code=201)
async def add_knowledge(
    entity_type: str, item: KnowledgeItem, db: TenantDB, user: CurrentUser
) -> dict:
    """Add a document to the agent's knowledge base."""
    _require_admin(user)
    persona = await _get_or_seed(entity_type, user.tenant_id, user.user_id, db)
    kb = list(persona.knowledge_base or [])
    kb.append({
        "title": item.title,
        "content": item.content,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    persona.knowledge_base = kb
    await db.flush()
    await db.commit()
    return {"count": len(kb), "added": item.title}


@router.delete("/{entity_type}/knowledge/{idx}", status_code=204)
async def remove_knowledge(
    entity_type: str, idx: int, db: TenantDB, user: CurrentUser
) -> None:
    _require_admin(user)
    persona = await _get_or_seed(entity_type, user.tenant_id, user.user_id, db)
    kb = list(persona.knowledge_base or [])
    if idx < 0 or idx >= len(kb):
        raise HTTPException(404, "Knowledge item not found")
    kb.pop(idx)
    persona.knowledge_base = kb
    await db.flush()
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(entity_type: str, tenant_id, db) -> AgentPersona:
    q = select(AgentPersona).where(
        AgentPersona.tenant_id == tenant_id,
        AgentPersona.entity_type == entity_type,
    )
    persona = (await db.execute(q)).scalar_one_or_none()
    if not persona:
        raise HTTPException(404, f"Persona '{entity_type}' not found")
    return persona


async def _get_or_seed(entity_type: str, tenant_id, created_by, db) -> AgentPersona:
    """Get from DB or seed from defaults (auto-create on first admin access)."""
    q = select(AgentPersona).where(
        AgentPersona.tenant_id == tenant_id,
        AgentPersona.entity_type == entity_type,
    )
    persona = (await db.execute(q)).scalar_one_or_none()
    if persona:
        return persona

    defaults = _DEFAULT_PERSONAS.get(entity_type)
    if not defaults:
        raise HTTPException(404, f"Persona '{entity_type}' not found")

    # Seed from defaults into DB so admin can now edit it
    persona = AgentPersona(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by=created_by,
        name=defaults["display_name"],
        display_name=defaults["display_name"],
        entity_type=entity_type,
        avatar_emoji=defaults.get("avatar_emoji", "🤖"),
        description=defaults.get("description"),
        system_prompt=defaults["system_prompt"],
        preferred_tier=defaults.get("preferred_tier", 2),
        is_default=True,
        is_enabled=True,
    )
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    return persona


def _persona_detail(p: AgentPersona) -> dict:
    return {
        "id": str(p.id),
        "entity_type": p.entity_type,
        "display_name": p.display_name,
        "avatar_emoji": p.avatar_emoji,
        "description": p.description,
        "system_prompt": p.system_prompt,
        "training_context_length": len(p.training_context or ""),
        "knowledge_base_count": len(p.knowledge_base or []),
        "knowledge_base": p.knowledge_base or [],
        "behavior_rules": p.behavior_rules or [],
        "tone_style": p.tone_style or {},
        "preferred_tier": p.preferred_tier,
        "preferred_model": p.preferred_model,
        "is_enabled": p.is_enabled,
        "is_default": p.is_default,
        "total_conversations": p.total_conversations,
        "last_trained_at": p.last_trained_at.isoformat() if p.last_trained_at else None,
        "created_at": p.created_at.isoformat(),
    }
