from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Returns operational status of all critical dependencies.
    Used by Docker healthcheck, load balancers, and the Admin Panel.
    """
    checks: dict[str, str] = {}

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # ── Redis ──────────────────────────────────────────────────────────────────
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # ── Keycloak ───────────────────────────────────────────────────────────────
    try:
        oidc_url = (
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
            "/.well-known/openid-configuration"
        )
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(oidc_url)
        checks["keycloak"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as exc:
        checks["keycloak"] = f"error: {exc}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
