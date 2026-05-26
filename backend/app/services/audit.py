"""
Audit trail service.

Every canonical object state mutation MUST call audit.record() in the same
database transaction as the mutation itself. Atomicity is guaranteed by
SQLAlchemy session — both writes commit or both roll back.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    async def record(
        self,
        session: AsyncSession,
        *,
        object_type: str,
        object_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,
        from_status: str | None = None,
        to_status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = AuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            occurred_at=datetime.now(timezone.utc),
            extra=metadata or {},
        )
        session.add(entry)


audit = AuditService()
