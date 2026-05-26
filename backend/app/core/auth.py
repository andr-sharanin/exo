import asyncio
import uuid
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

security = HTTPBearer()


class TokenClaims(BaseModel):
    sub: str
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str | None = None
    roles: list[str] = []


class _JWKSCache:
    """Thread-safe JWKS cache with double-checked locking and key rotation support."""

    def __init__(self) -> None:
        self._cache: dict | None = None
        self._lock = asyncio.Lock()

    @property
    def _jwks_url(self) -> str:
        return (
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
            "/protocol/openid-connect/certs"
        )

    async def _fetch(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
            return resp.json()

    async def get(self) -> dict:
        if self._cache is None:
            async with self._lock:
                if self._cache is None:
                    self._cache = await self._fetch()
        return self._cache

    async def refresh(self) -> dict:
        """Called on signature validation failure — handles key rotation."""
        async with self._lock:
            self._cache = await self._fetch()
        return self._cache


_jwks_cache = _JWKSCache()


def _extract_claims(payload: dict) -> TokenClaims:
    sub = payload.get("sub", "")
    # tenant_id: custom claim injected by Keycloak mapper, or sub as fallback
    tenant_raw = payload.get("tenant_id") or sub
    roles: list[str] = payload.get("realm_access", {}).get("roles", [])
    return TokenClaims(
        sub=sub,
        user_id=uuid.UUID(sub),
        tenant_id=uuid.UUID(str(tenant_raw)),
        email=payload.get("email"),
        roles=roles,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenClaims:
    token = credentials.credentials
    try:
        jwks = await _jwks_cache.get()
        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            # Key may have rotated — refresh once and retry
            jwks = await _jwks_cache.refresh()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        return _extract_claims(payload)
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


def require_role(role: str):
    """Dependency factory: raises 403 if user doesn't have the required role."""

    async def _check(user: CurrentUser) -> TokenClaims:
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: '{role}'",
            )
        return user

    return Depends(_check)
