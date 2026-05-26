"""
Team management API — requires Team tier subscription.

POST   /team/invitations           — invite a new member by email
GET    /team/invitations           — list all invitations for the tenant
DELETE /team/invitations/{id}      — revoke a pending invitation
POST   /team/invitations/accept    — accept an invitation by token (any authenticated user)
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.team_invitation import TeamInvitation

router = APIRouter(prefix="/team", tags=["team"])

_INVITE_TTL_DAYS = 7


class InviteRequest(BaseModel):
    email: EmailStr


@router.post("/invitations", status_code=201)
async def create_invitation(
    body: InviteRequest, db: TenantDB, user: CurrentUser
) -> dict:
    """Create an invitation link for the given email. Requires Team tier."""
    from app.services.subscription_service import SubscriptionService
    tier = await SubscriptionService(db).get_tier(user.user_id, user.tenant_id)
    if tier != "team":
        raise HTTPException(
            402,
            "Приглашения в команду доступны только на Team тарифе. "
            "Перейдите на Team план в настройках подписки.",
        )

    # Check for existing pending invite to same email
    existing = (await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.tenant_id == user.tenant_id,
            TeamInvitation.email == body.email,
            TeamInvitation.status == "pending",
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Приглашение для {body.email} уже отправлено.")

    invite = TeamInvitation(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        invited_by_user_id=user.user_id,
        email=body.email,
        status="pending",
        token=secrets.token_urlsafe(48),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.flush()
    await db.commit()

    # Send invitation email (non-blocking — failure does not abort the request)
    from app.services.email_service import send_email
    from app.core.config import settings
    join_url = f"{settings.BASE_URL}/settings/team/join?token={invite.token}"
    await send_email(
        to=body.email,
        subject="Вас приглашают в команду ExoCortex",
        body_html=_invite_email_html(join_url, _INVITE_TTL_DAYS),
        body_text=f"Вас приглашают в ExoCortex. Перейдите по ссылке: {join_url}",
        db=db,
    )

    return _invite_response(invite)


@router.get("/invitations")
async def list_invitations(db: TenantDB, user: CurrentUser) -> list[dict]:
    """Return all invitations for the current tenant."""
    from app.services.subscription_service import SubscriptionService
    tier = await SubscriptionService(db).get_tier(user.user_id, user.tenant_id)
    if tier != "team":
        raise HTTPException(402, "Team тариф обязателен для управления командой.")

    rows = list((await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.tenant_id == user.tenant_id)
        .order_by(TeamInvitation.created_at.desc())
    )).scalars().all())
    return [_invite_response(r) for r in rows]


@router.delete("/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> None:
    """Revoke a pending invitation."""
    invite = (await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.id == invitation_id,
            TeamInvitation.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if not invite:
        raise HTTPException(404, "Invitation not found")
    if invite.status != "pending":
        raise HTTPException(409, "Можно отозвать только pending приглашения.")
    invite.status = "revoked"
    await db.flush()
    await db.commit()


@router.post("/invitations/accept")
async def accept_invitation(
    db: TenantDB,
    user: CurrentUser,
    token: str = Query(..., description="Invitation token from the email link"),
) -> dict:
    """Accept a team invitation by token. The authenticated user becomes the accepted member."""
    from app.core.database import AsyncSessionLocal

    # Look up the invitation globally (not filtered by tenant — the user is joining a new tenant)
    async with AsyncSessionLocal() as global_db:
        invite = (await global_db.execute(
            select(TeamInvitation).where(TeamInvitation.token == token)
        )).scalar_one_or_none()

        if not invite:
            raise HTTPException(404, "Приглашение не найдено.")
        if invite.status != "pending":
            raise HTTPException(409, f"Приглашение уже обработано (статус: {invite.status}).")
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(410, "Срок действия приглашения истёк.")

        invite.status = "accepted"
        invite.accepted_at = datetime.now(timezone.utc)
        invite.accepted_by_user_id = user.user_id
        await global_db.flush()
        await global_db.commit()
        return _invite_response(invite)


@router.get("/invitations/lookup")
async def lookup_invitation(token: str = Query(...)) -> dict:
    """Public lookup — returns invitation details by token (for the join page preview)."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as global_db:
        invite = (await global_db.execute(
            select(TeamInvitation).where(TeamInvitation.token == token)
        )).scalar_one_or_none()

    if not invite:
        raise HTTPException(404, "Приглашение не найдено.")
    return {
        "email": invite.email,
        "status": invite.status,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
    }


def _invite_response(inv: TeamInvitation) -> dict:
    return {
        "id": str(inv.id),
        "email": inv.email,
        "status": inv.status,
        "created_at": inv.created_at.isoformat(),
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
    }


def _invite_email_html(join_url: str, ttl_days: int) -> str:
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f0f1a;color:#e2e8f0;padding:40px;">
  <div style="max-width:480px;margin:0 auto;background:#1a1a2e;border-radius:12px;padding:32px;">
    <h2 style="color:#a78bfa;margin-top:0;">Приглашение в команду ExoCortex</h2>
    <p>Вас приглашают присоединиться к рабочему пространству ExoCortex.</p>
    <p style="color:#94a3b8;font-size:14px;">
      Ссылка действительна в течение {ttl_days} дней.
    </p>
    <a href="{join_url}"
       style="display:inline-block;margin-top:16px;padding:12px 24px;
              background:#7c3aed;color:#fff;border-radius:8px;
              text-decoration:none;font-weight:600;">
      Принять приглашение →
    </a>
    <p style="margin-top:24px;color:#64748b;font-size:12px;">
      Если вы не ожидали этого письма — просто проигнорируйте его.
    </p>
  </div>
</body>
</html>
"""
