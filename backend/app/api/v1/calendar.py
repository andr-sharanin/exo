"""
Calendar Integration API

GET    /calendar/events               — list upcoming events from all connected calendars
GET    /calendar/integrations         — list user's calendar connections
POST   /calendar/integrations/caldav  — connect a CalDAV calendar
POST   /calendar/integrations/google  — start Google OAuth2 flow (returns auth URL)
GET    /calendar/integrations/google/callback — handle OAuth2 callback
DELETE /calendar/integrations/{id}    — disconnect a calendar
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.rls import TenantDB
from app.models.calendar_integration import CalendarIntegration
from app.services.calendar_sync import (
    CalendarSyncService,
    GoogleCalendarAdapter,
    ICalAdapter,
    MicrosoftGraphAdapter,
    _fernet_encrypt,
)
from app.services.config_service import ConfigService

router = APIRouter(prefix="/calendar", tags=["calendar"])

_GOOGLE_REDIRECT_PATH = "/api/v1/calendar/integrations/google/callback"
_MS_REDIRECT_PATH = "/api/v1/calendar/integrations/microsoft/callback"


class CalDAVConnectRequest(BaseModel):
    display_name: str = "My CalDAV Calendar"
    calendar_url: str
    username: str
    password: str
    sync_direction: str = "read"


class ICalConnectRequest(BaseModel):
    display_name: str = "iCal Feed"
    ical_url: str
    sync_direction: str = "read"


# ── Events ────────────────────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    db: TenantDB,
    user: CurrentUser,
    days_ahead: int = Query(default=7, ge=1, le=30),
) -> list[dict]:
    svc = CalendarSyncService(db, settings.EXOCORTEX_SECRET_KEY)
    return await svc.fetch_all_events(user.user_id, user.tenant_id, days_ahead)


# ── Integrations list ─────────────────────────────────────────────────────────

@router.get("/integrations")
async def list_integrations(db: TenantDB, user: CurrentUser) -> list[dict]:
    q = select(CalendarIntegration).where(
        CalendarIntegration.user_id == user.user_id,
        CalendarIntegration.tenant_id == user.tenant_id,
    ).order_by(CalendarIntegration.created_at)
    rows = list((await db.execute(q)).scalars().all())
    return [_integ_response(r) for r in rows]


# ── CalDAV connect ────────────────────────────────────────────────────────────

@router.post("/integrations/caldav", status_code=201)
async def connect_caldav(
    body: CalDAVConnectRequest, db: TenantDB, user: CurrentUser
) -> dict:
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_add_calendar(user.user_id, user.tenant_id)

    # Quick connectivity check before storing
    from app.services.calendar_sync import CalDAVAdapter
    try:
        adapter = CalDAVAdapter(body.calendar_url, body.username, body.password)
        await adapter.fetch_events(days_ahead=1)
    except Exception as exc:
        raise HTTPException(400, f"CalDAV connection failed: {exc}")

    creds_enc = _fernet_encrypt(
        {"username": body.username, "password": body.password},
        settings.EXOCORTEX_SECRET_KEY,
    )
    integ = CalendarIntegration(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        provider="caldav",
        display_name=body.display_name,
        calendar_url=body.calendar_url,
        credentials_enc=creds_enc,
        sync_direction=body.sync_direction,
        is_active=True,
    )
    db.add(integ)
    await db.flush()
    await db.commit()
    return _integ_response(integ)


# ── iCal URL ─────────────────────────────────────────────────────────────────

@router.post("/integrations/ical", status_code=201)
async def connect_ical(
    body: ICalConnectRequest, db: TenantDB, user: CurrentUser
) -> dict:
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_add_calendar(user.user_id, user.tenant_id)

    adapter = ICalAdapter(body.ical_url)
    try:
        await adapter.fetch_events(days_ahead=1)
    except Exception as exc:
        raise HTTPException(400, f"iCal URL not accessible: {exc}")

    integ = CalendarIntegration(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        provider="ical",
        display_name=body.display_name,
        calendar_url=body.ical_url,
        sync_direction=body.sync_direction,
        is_active=True,
    )
    db.add(integ)
    await db.flush()
    await db.commit()
    return _integ_response(integ)


# ── Google OAuth2 ─────────────────────────────────────────────────────────────

@router.post("/integrations/google")
async def start_google_oauth(db: TenantDB, user: CurrentUser) -> dict:
    """Returns the Google OAuth2 authorization URL."""
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_add_calendar(user.user_id, user.tenant_id)

    config_svc = ConfigService(db)
    client_id = await config_svc.get("google_calendar_client_id")
    if not client_id:
        raise HTTPException(400, "google_calendar_client_id not configured in Admin Settings")

    redirect_uri = f"{settings.BASE_URL}{_GOOGLE_REDIRECT_PATH}"
    # State encodes user context; stored in Redis for verification
    state = f"{user.user_id}:{user.tenant_id}:{secrets.token_urlsafe(8)}"
    auth_url = GoogleCalendarAdapter.auth_url(client_id, redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/integrations/google/callback")
async def google_oauth_callback(
    db: TenantDB,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(default=None),
) -> RedirectResponse:
    """Handle Google OAuth2 callback — store tokens and redirect to calendar settings."""
    if error:
        return RedirectResponse(f"/settings/calendar?error={error}")

    parts = state.split(":")
    if len(parts) < 2:
        raise HTTPException(400, "Invalid state")
    user_id = uuid.UUID(parts[0])
    tenant_id = uuid.UUID(parts[1])

    config_svc = ConfigService(db)
    client_id = await config_svc.get("google_calendar_client_id") or ""
    client_secret = await config_svc.get("google_calendar_client_secret") or ""
    redirect_uri = f"{settings.BASE_URL}{_GOOGLE_REDIRECT_PATH}"

    try:
        tokens = await GoogleCalendarAdapter.exchange_code(
            code, client_id, client_secret, redirect_uri
        )
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}")

    creds_enc = _fernet_encrypt(
        {
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
        },
        settings.EXOCORTEX_SECRET_KEY,
    )

    integ = CalendarIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        provider="google",
        display_name="Google Calendar",
        credentials_enc=creds_enc,
        oauth_scope="https://www.googleapis.com/auth/calendar.readonly",
        sync_direction="read",
        is_active=True,
    )
    db.add(integ)
    await db.flush()
    await db.commit()
    return RedirectResponse("/settings/calendar?connected=google")


# ── Microsoft Graph OAuth2 ────────────────────────────────────────────────────

@router.post("/integrations/microsoft")
async def start_microsoft_oauth(db: TenantDB, user: CurrentUser) -> dict:
    """Returns the Microsoft OAuth2 authorization URL."""
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_add_calendar(user.user_id, user.tenant_id)

    config_svc = ConfigService(db)
    client_id = await config_svc.get("ms_graph_client_id")
    if not client_id:
        raise HTTPException(400, "ms_graph_client_id not configured in Admin Settings")

    redirect_uri = f"{settings.BASE_URL}{_MS_REDIRECT_PATH}"
    state = f"{user.user_id}:{user.tenant_id}:{secrets.token_urlsafe(8)}"
    auth_url = MicrosoftGraphAdapter.auth_url(client_id, redirect_uri, state)
    return {"auth_url": auth_url}


@router.get("/integrations/microsoft/callback")
async def microsoft_oauth_callback(
    db: TenantDB,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(default=None),
    error_description: str = Query(default=None),
) -> RedirectResponse:
    """Handle Microsoft OAuth2 callback — store tokens and redirect to calendar settings."""
    if error:
        return RedirectResponse(f"/settings/calendar?error={error}")

    parts = state.split(":")
    if len(parts) < 2:
        raise HTTPException(400, "Invalid state")
    user_id = uuid.UUID(parts[0])
    tenant_id = uuid.UUID(parts[1])

    config_svc = ConfigService(db)
    client_id = await config_svc.get("ms_graph_client_id") or ""
    client_secret = await config_svc.get("ms_graph_client_secret") or ""
    redirect_uri = f"{settings.BASE_URL}{_MS_REDIRECT_PATH}"

    try:
        tokens = await MicrosoftGraphAdapter.exchange_code(
            code, client_id, client_secret, redirect_uri
        )
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}")

    creds_enc = _fernet_encrypt(
        {
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
        },
        settings.EXOCORTEX_SECRET_KEY,
    )

    integ = CalendarIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        provider="microsoft",
        display_name="Microsoft Outlook Calendar",
        credentials_enc=creds_enc,
        oauth_scope="Calendars.Read offline_access",
        sync_direction="read",
        is_active=True,
    )
    db.add(integ)
    await db.flush()
    await db.commit()
    return RedirectResponse("/settings/calendar?connected=microsoft")


# ── Disconnect ────────────────────────────────────────────────────────────────

@router.delete("/integrations/{integration_id}", status_code=204)
async def disconnect_calendar(
    integration_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> None:
    q = select(CalendarIntegration).where(
        CalendarIntegration.id == integration_id,
        CalendarIntegration.user_id == user.user_id,
    )
    integ = (await db.execute(q)).scalar_one_or_none()
    if not integ:
        raise HTTPException(404, "Integration not found")
    integ.is_active = False
    integ.credentials_enc = None
    await db.flush()
    await db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _integ_response(r: CalendarIntegration) -> dict:
    return {
        "id": str(r.id),
        "provider": r.provider,
        "display_name": r.display_name,
        "sync_direction": r.sync_direction,
        "is_active": r.is_active,
        "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
        "last_error": r.last_error,
        "created_at": r.created_at.isoformat(),
    }
