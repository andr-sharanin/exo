"""
Calendar Sync Service — reads events from CalDAV and Google Calendar.

Uses httpx only (no caldav library dependency).
CalDAV: REPORT request with VEVENT filter.
Google: REST API with stored OAuth2 tokens.

All credentials are Fernet-encrypted in CalendarIntegration.credentials_enc.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

_CALDAV_REPORT = """<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:getetag/>
    <c:calendar-data/>
  </d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{start}" end="{end}"/>
      </c:comp-filter>
    </c:comp-filter>
  </c:filter>
</c:calendar-query>"""

_GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# Microsoft Graph
_MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_MS_EVENTS_URL = "https://graph.microsoft.com/v1.0/me/calendarview"
_MS_TOKEN_CHECK_URL = "https://graph.microsoft.com/v1.0/me"  # cheap call to test token validity


def _fernet_decrypt(enc: str, secret_key: str) -> dict:
    from cryptography.fernet import Fernet
    f = Fernet(secret_key.encode())
    return json.loads(f.decrypt(enc.encode()).decode())


def _fernet_encrypt(data: dict, secret_key: str) -> str:
    from cryptography.fernet import Fernet
    f = Fernet(secret_key.encode())
    return f.encrypt(json.dumps(data).encode()).decode()


def _parse_ical_date(value: str) -> str:
    """Convert YYYYMMDDTHHMMSSZ or YYYYMMDD to ISO 8601."""
    value = value.strip()
    if "T" in value:
        dt = datetime.strptime(value.replace("Z", ""), "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return datetime.strptime(value, "%Y%m%d").date().isoformat()


def _parse_vevent(vevent_text: str) -> dict | None:
    """Extract key fields from a VEVENT text block."""
    def _get(key: str) -> str | None:
        m = re.search(rf"^{key}[;:][^\r\n]*", vevent_text, re.MULTILINE)
        if not m:
            return None
        line = m.group(0)
        return line.split(":", 1)[-1].strip() if ":" in line else None

    summary = _get("SUMMARY")
    dtstart = _get("DTSTART")
    dtend = _get("DTEND")
    uid = _get("UID")
    if not summary or not dtstart:
        return None
    return {
        "uid": uid or "",
        "summary": summary,
        "start": _parse_ical_date(dtstart),
        "end": _parse_ical_date(dtend) if dtend else None,
        "description": _get("DESCRIPTION") or "",
        "location": _get("LOCATION") or "",
    }


class CalDAVAdapter:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth = (username, password)

    async def fetch_events(self, days_ahead: int = 7) -> list[dict]:
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y%m%dT%H%M%SZ")
        end = (now + timedelta(days=days_ahead)).strftime("%Y%m%dT%H%M%SZ")
        body = _CALDAV_REPORT.format(start=start, end=end)
        headers = {
            "Content-Type": "application/xml",
            "Depth": "1",
        }
        async with httpx.AsyncClient(auth=self._auth, timeout=15.0) as client:
            resp = await client.request(
                "REPORT", self.base_url, content=body, headers=headers
            )
            resp.raise_for_status()

        events = []
        for match in re.finditer(r"BEGIN:VEVENT(.*?)END:VEVENT", resp.text, re.DOTALL):
            parsed = _parse_vevent(match.group(1))
            if parsed:
                events.append(parsed)
        return events


class ICalAdapter:
    """Fetches and parses a public iCal (.ics) feed URL."""

    def __init__(self, ical_url: str) -> None:
        self.ical_url = ical_url

    async def fetch_events(self, days_ahead: int = 7) -> list[dict]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(self.ical_url)
            resp.raise_for_status()
        return _parse_ical_text(resp.text, days_ahead)


def _parse_ical_text(text: str, days_ahead: int = 7) -> list[dict]:
    """Parse all VEVENTs from iCal text, filter to next `days_ahead` days."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)
    events = []
    for match in re.finditer(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.DOTALL):
        parsed = _parse_vevent(match.group(1))
        if not parsed:
            continue
        # Filter by date range: only upcoming events
        try:
            start_str = parsed["start"]
            if "T" in start_str:
                start_dt = datetime.fromisoformat(start_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                start_dt = datetime(
                    *[int(x) for x in start_str.split("-")], tzinfo=timezone.utc
                )
            if start_dt >= now and start_dt <= cutoff:
                events.append(parsed)
        except (ValueError, TypeError):
            events.append(parsed)  # include if we can't parse the date
    return events


class GoogleCalendarAdapter:
    def __init__(self, access_token: str, refresh_token: str,
                 client_id: str, client_secret: str) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret

    async def _ensure_token(self) -> str:
        """Refresh access token if needed. Returns valid access token."""
        # Try current token first
        async with httpx.AsyncClient(timeout=10.0) as client:
            test = await client.get(
                "https://www.googleapis.com/oauth2/v1/tokeninfo",
                params={"access_token": self._access_token}
            )
            if test.status_code == 200:
                return self._access_token

            # Refresh
            resp = await client.post(_GOOGLE_TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def fetch_events(self, days_ahead: int = 7) -> list[dict]:
        token = await self._ensure_token()
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _GOOGLE_EVENTS_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 50,
                },
            )
            resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "uid": item.get("id", ""),
                "summary": item.get("summary", ""),
                "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", ""),
                "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "html_link": item.get("htmlLink", ""),
            }
            for item in items
            if item.get("summary")
        ]

    @staticmethod
    def auth_url(client_id: str, redirect_uri: str, state: str) -> str:
        import urllib.parse
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    async def exchange_code(
        code: str, client_id: str, client_secret: str, redirect_uri: str
    ) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()


class MicrosoftGraphAdapter:
    """
    Fetches calendar events from Microsoft Graph API (Office 365 / Outlook).

    Uses OAuth2 authorization code flow with offline_access for refresh tokens.
    Token refresh is handled transparently: a 401 on the first request triggers
    a token refresh and one retry.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret

    async def _refresh_access_token(self) -> str:
        """Use the refresh_token to get a new access_token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _MS_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "Calendars.Read offline_access",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            if "refresh_token" in data:
                self._refresh_token = data["refresh_token"]
            return self._access_token

    async def fetch_events(self, days_ahead: int = 7) -> list[dict]:
        now = datetime.now(timezone.utc)
        time_start = now.isoformat()
        time_end = (now + timedelta(days=days_ahead)).isoformat()
        params = {
            "startDateTime": time_start,
            "endDateTime": time_end,
            "$select": "id,subject,start,end,bodyPreview,location,webLink",
            "$top": 50,
            "$orderby": "start/dateTime",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _MS_EVENTS_URL,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Prefer": 'outlook.timezone="UTC"',
                },
                params=params,
            )
            if resp.status_code == 401:
                # Token expired — refresh and retry once
                await self._refresh_access_token()
                resp = await client.get(
                    _MS_EVENTS_URL,
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Prefer": 'outlook.timezone="UTC"',
                    },
                    params=params,
                )
            resp.raise_for_status()

        items = resp.json().get("value", [])
        return [
            {
                "uid": item.get("id", ""),
                "summary": item.get("subject", ""),
                "start": (item.get("start") or {}).get("dateTime", ""),
                "end": (item.get("end") or {}).get("dateTime"),
                "description": item.get("bodyPreview", ""),
                "location": (item.get("location") or {}).get("displayName", ""),
                "html_link": item.get("webLink", ""),
            }
            for item in items
            if item.get("subject")
        ]

    @staticmethod
    def auth_url(client_id: str, redirect_uri: str, state: str) -> str:
        import urllib.parse

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "Calendars.Read offline_access",
            "state": state,
        }
        return f"{_MS_AUTH_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    async def exchange_code(
        code: str, client_id: str, client_secret: str, redirect_uri: str
    ) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _MS_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "Calendars.Read offline_access",
                },
            )
            resp.raise_for_status()
            return resp.json()


class CalendarSyncService:
    """
    High-level service: fetches events from all active integrations for a user.
    """

    def __init__(self, db, secret_key: str) -> None:
        self._db = db
        self._secret_key = secret_key

    async def fetch_all_events(self, user_id, tenant_id, days_ahead: int = 7) -> list[dict]:
        from sqlalchemy import select
        from app.models.calendar_integration import CalendarIntegration
        from app.core.config import settings

        q = select(CalendarIntegration).where(
            CalendarIntegration.user_id == user_id,
            CalendarIntegration.tenant_id == tenant_id,
            CalendarIntegration.is_active == True,  # noqa: E712
        )
        integrations = list((await self._db.execute(q)).scalars().all())

        all_events: list[dict] = []
        for integ in integrations:
            try:
                events = await self._fetch_for_integration(integ, days_ahead)
                for e in events:
                    e["source"] = integ.display_name
                    e["provider"] = integ.provider
                all_events.extend(events)

                integ.last_synced_at = datetime.now(timezone.utc)
                integ.last_error = None
            except Exception as exc:
                integ.last_error = str(exc)[:1024]

        await self._db.flush()
        all_events.sort(key=lambda e: e.get("start", ""))
        return all_events

    async def _fetch_for_integration(
        self, integ, days_ahead: int
    ) -> list[dict]:
        creds = (
            _fernet_decrypt(integ.credentials_enc, self._secret_key)
            if integ.credentials_enc
            else {}
        )
        if integ.provider == "ical":
            adapter = ICalAdapter(integ.calendar_url or "")
            return await adapter.fetch_events(days_ahead)

        if integ.provider == "caldav":
            adapter = CalDAVAdapter(
                integ.calendar_url or "",
                creds.get("username", ""),
                creds.get("password", ""),
            )
            return await adapter.fetch_events(days_ahead)

        if integ.provider == "google":
            from app.services.config_service import ConfigService
            svc = ConfigService(self._db)
            client_id = await svc.get("google_calendar_client_id") or ""
            client_secret = await svc.get("google_calendar_client_secret") or ""
            adapter = GoogleCalendarAdapter(
                access_token=creds.get("access_token", ""),
                refresh_token=creds.get("refresh_token", ""),
                client_id=client_id,
                client_secret=client_secret,
            )
            return await adapter.fetch_events(days_ahead)

        if integ.provider == "microsoft":
            from app.services.config_service import ConfigService
            svc = ConfigService(self._db)
            client_id = await svc.get("ms_graph_client_id") or ""
            client_secret = await svc.get("ms_graph_client_secret") or ""
            adapter = MicrosoftGraphAdapter(
                access_token=creds.get("access_token", ""),
                refresh_token=creds.get("refresh_token", ""),
                client_id=client_id,
                client_secret=client_secret,
            )
            return await adapter.fetch_events(days_ahead)

        return []
