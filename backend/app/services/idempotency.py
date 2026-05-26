"""
Idempotency enforcement for Command ingress.

Strategy: unique DB constraint on (tenant_id, idempotency_key).
On conflict → return existing Command ID instead of raising.
No Redis needed — DB index is the source of truth.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import Command


class IdempotencyConflictError(Exception):
    """Idempotency key already used — caller should return the existing object."""

    def __init__(self, existing_id: uuid.UUID) -> None:
        super().__init__(f"Idempotency key already used — existing id: {existing_id}")
        self.existing_id = existing_id


async def check_idempotency(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
) -> uuid.UUID | None:
    """
    Returns the existing Command.id if the key was already used, else None.
    Call before inserting a new Command.
    """
    result = await session.execute(
        select(Command.id).where(
            Command.tenant_id == tenant_id,
            Command.idempotency_key == idempotency_key,
        )
    )
    row = result.scalar_one_or_none()
    return row
