"""
Phase 6 — Admin Panel API (backend only).

All endpoints require the "admin" role via require_role().

GET  /admin/health    — system health + AI tier config summary
GET  /admin/audit     — paginated audit log (tenant-scoped for admin, cross-tenant for system_admin)
GET  /admin/ai-stats  — AI inference usage statistics
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.auth import TokenClaims, require_role
from app.core.rls import TenantDB
from app.repositories.ai_repos import AIRequestLogRepo, AuditLogRepo
from app.schemas.ai_schemas import (
    AdminAuditResponse,
    AdminHealthResponse,
    AIStatsResponse,
    AuditLogItem,
)
from app.services.ai_router import AITier

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[TokenClaims, require_role("admin")]


@router.get("/health", response_model=AdminHealthResponse)
async def admin_health(user: AdminUser) -> AdminHealthResponse:
    return AdminHealthResponse(
        status="healthy",
        ai_tiers=[tier.value for tier in AITier],
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/audit", response_model=AdminAuditResponse)
async def admin_audit(
    user: AdminUser,
    db: TenantDB,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AdminAuditResponse:
    repo = AuditLogRepo(db)
    # tenant_admin sees own tenant; system_admin (has "system_admin" role) sees all
    tenant_filter = (
        None if "system_admin" in user.roles else user.tenant_id
    )
    items, total = await repo.list_paginated(
        tenant_id=tenant_filter, limit=limit, offset=offset
    )
    return AdminAuditResponse(
        items=[AuditLogItem.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/ai-stats", response_model=AIStatsResponse)
async def admin_ai_stats(
    user: AdminUser,
    db: TenantDB,
) -> AIStatsResponse:
    stats = await AIRequestLogRepo(db).stats_by_tenant(user.tenant_id)
    return AIStatsResponse(**stats)
