"""
Row Level Security tenant isolation.

Every authenticated API request must use TenantDB instead of raw get_db.
This sets the PostgreSQL session variable that RLS policies read.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, TokenClaims
from app.core.database import get_db


async def get_tenant_db(
    db: AsyncSession = Depends(get_db),
    user: TokenClaims = Depends(get_current_user),
) -> AsyncSession:
    """
    Returns a DB session with RLS tenant context set.
    SET LOCAL applies only to the current transaction — safe with connection pooling.
    """
    await db.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(user.tenant_id)},
    )
    return db


TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]
