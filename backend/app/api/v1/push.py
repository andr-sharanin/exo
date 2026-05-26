"""
Phase 9 — Web Push Notification API

POST /push/subscribe   — register a push subscription (browser/device)
GET  /push/vapid-key   — return VAPID public key for browser subscription setup
"""
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.push_subscription import PushSubscription
from app.repositories.config_repos import PushSubscriptionRepo
from app.services.config_service import ConfigService

router = APIRouter(prefix="/push", tags=["push"])


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str | None = None
    auth: str | None = None
    device_name: str | None = None


class PushSubscriptionResponse(BaseModel):
    id: uuid.UUID
    endpoint: str
    device_name: str | None
    created_at: str

    class Config:
        from_attributes = True


class VapidKeyResponse(BaseModel):
    public_key: str


@router.get("/vapid-key", response_model=VapidKeyResponse)
async def get_vapid_key() -> VapidKeyResponse:
    """Return VAPID public key. Browser needs this to create a push subscription."""
    public_key = ConfigService.get_from_env("VAPID_PUBLIC_KEY", default="")
    return VapidKeyResponse(public_key=public_key)


@router.post("/subscribe", response_model=PushSubscriptionResponse, status_code=201)
async def subscribe(
    body: PushSubscribeRequest, db: TenantDB, user: CurrentUser
) -> PushSubscriptionResponse:
    sub = await PushSubscriptionRepo(db).create(
        PushSubscription(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
            device_name=body.device_name,
        )
    )
    return PushSubscriptionResponse(
        id=sub.id,
        endpoint=sub.endpoint,
        device_name=sub.device_name,
        created_at=sub.created_at.isoformat(),
    )
