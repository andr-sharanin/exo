"""Repositories for Phase 6: AIRequestLog and AuditLog (admin)."""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_request_log import AIRequestLog
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AIRequestLogRepo(BaseRepository[AIRequestLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIRequestLog, session)

    async def stats_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> dict:
        """Aggregate AI usage stats for a tenant."""
        rows = await self._session.execute(
            select(
                AIRequestLog.tier,
                AIRequestLog.status,
                AIRequestLog.was_fallback,
                func.count().label("cnt"),
                func.sum(AIRequestLog.prompt_tokens).label("pt"),
                func.sum(AIRequestLog.completion_tokens).label("ct"),
            )
            .where(AIRequestLog.tenant_id == tenant_id)
            .group_by(AIRequestLog.tier, AIRequestLog.status, AIRequestLog.was_fallback)
        )
        results = rows.all()

        total = 0
        by_tier: dict[str, int] = {}
        total_prompt = 0
        total_completion = 0
        success_count = 0
        fallback_count = 0

        for row in results:
            cnt = row.cnt
            total += cnt
            by_tier[row.tier] = by_tier.get(row.tier, 0) + cnt
            total_prompt += row.pt or 0
            total_completion += row.ct or 0
            if row.status == "success":
                success_count += cnt
            if row.was_fallback:
                fallback_count += cnt

        return {
            "total_requests": total,
            "by_tier": by_tier,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "success_rate": success_count / total if total else 1.0,
            "fallback_rate": fallback_count / total if total else 0.0,
        }


class AuditLogRepo:
    """Read-only repository for the audit_log table (no RLS — admin access)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_paginated(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        q = select(AuditLog)
        q_count = select(func.count()).select_from(AuditLog)
        if tenant_id is not None:
            q = q.where(AuditLog.tenant_id == tenant_id)
            q_count = q_count.where(AuditLog.tenant_id == tenant_id)

        total_result = await self._session.execute(q_count)
        total = total_result.scalar_one()

        q = q.order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset)
        items_result = await self._session.execute(q)
        items = list(items_result.scalars().all())

        return items, total
