"""
Phase 9 — System Configuration API (system_admin only)

GET  /admin/config          — list all config entries (secrets masked)
GET  /admin/config/{key}    — get single entry (secret masked)
PUT  /admin/config/{key}    — upsert config entry

After writing a secret key, the value is encrypted before storage.
API responses never return raw secret values — only masked previews.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.auth import TokenClaims, require_role
from app.core.rls import TenantDB
from app.models.system_config import SystemConfig
from app.repositories.config_repos import SystemConfigRepo
from app.services.config_service import ConfigService
from typing import Annotated

router = APIRouter(tags=["admin-config"])

SysAdmin = Annotated[TokenClaims, require_role("system_admin")]


class ConfigEntryWrite(BaseModel):
    value: str
    is_secret: bool = False
    description: str = ""
    category: str = "misc"


class ConfigEntryResponse(BaseModel):
    key: str
    value: str          # raw for non-secret, masked for secret
    is_secret: bool
    description: str
    category: str
    updated_at: datetime


def _to_response(entry: SystemConfig) -> ConfigEntryResponse:
    display_value = (
        ConfigService.mask_secret(ConfigService.decrypt(entry.value))
        if entry.is_secret
        else entry.value
    )
    return ConfigEntryResponse(
        key=entry.key,
        value=display_value,
        is_secret=entry.is_secret,
        description=entry.description,
        category=entry.category,
        updated_at=entry.updated_at,
    )


@router.get("/admin/config", response_model=list[ConfigEntryResponse])
async def list_config(user: SysAdmin, db: TenantDB) -> list[ConfigEntryResponse]:
    now = datetime.now(timezone.utc)
    saved = {e.key: e for e in await SystemConfigRepo(db).get_all()}

    result: list[ConfigEntryResponse] = []
    for key, meta in ConfigService.KNOWN_KEYS.items():
        if key in saved:
            result.append(_to_response(saved[key]))
        else:
            result.append(ConfigEntryResponse(
                key=key,
                value="",
                is_secret=meta["is_secret"],
                description=meta["description"],
                category=meta["category"],
                updated_at=now,
            ))

    # user-defined keys not in KNOWN_KEYS
    for key, entry in saved.items():
        if key not in ConfigService.KNOWN_KEYS:
            result.append(_to_response(entry))

    return result


@router.get("/admin/config/{key}", response_model=ConfigEntryResponse)
async def get_config_entry(key: str, user: SysAdmin, db: TenantDB) -> ConfigEntryResponse:
    entry = await SystemConfigRepo(db).get_by_key(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return _to_response(entry)


@router.put("/admin/config/{key}", response_model=ConfigEntryResponse)
async def set_config_entry(
    key: str, body: ConfigEntryWrite, user: SysAdmin, db: TenantDB
) -> ConfigEntryResponse:
    stored_value = (
        ConfigService.encrypt(body.value) if body.is_secret else body.value
    )
    entry = await SystemConfigRepo(db).upsert(
        SystemConfig(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            key=key,
            value=stored_value,
            is_secret=body.is_secret,
            description=body.description,
            category=body.category,
        )
    )
    # Sync AI keys to env immediately so LiteLLM picks them up without restart
    if key in ("anthropic_api_key", "openai_api_key") and body.value:
        import os
        env_map = {"anthropic_api_key": "ANTHROPIC_API_KEY", "openai_api_key": "OPENAI_API_KEY"}
        os.environ[env_map[key]] = body.value

    return _to_response(entry)
