"""
Unit tests for CalDAV and Google Calendar adapters.

All HTTP calls are intercepted with httpx.MockTransport — no real network.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from app.services.calendar_sync import (
    CalDAVAdapter,
    GoogleCalendarAdapter,
    MicrosoftGraphAdapter,
    _parse_ical_date,
    _parse_vevent,
    _fernet_encrypt,
    _fernet_decrypt,
)


# ── _parse_ical_date ──────────────────────────────────────────────────────────

def test_parse_ical_date_utc_datetime():
    result = _parse_ical_date("20260525T090000Z")
    assert "2026-05-25" in result
    assert "09:00:00" in result


def test_parse_ical_date_allday():
    result = _parse_ical_date("20260525")
    assert result == "2026-05-25"


def test_parse_ical_date_strips_whitespace():
    result = _parse_ical_date("  20260525  ")
    assert result == "2026-05-25"


# ── _parse_vevent ─────────────────────────────────────────────────────────────

_SAMPLE_VEVENT = """
UID:abc-123@example.com
DTSTART:20260525T100000Z
DTEND:20260525T110000Z
SUMMARY:Team standup
DESCRIPTION:Daily sync
LOCATION:Zoom
"""

def test_parse_vevent_extracts_fields():
    result = _parse_vevent(_SAMPLE_VEVENT)
    assert result is not None
    assert result["summary"] == "Team standup"
    assert "2026-05-25" in result["start"]
    assert result["description"] == "Daily sync"
    assert result["location"] == "Zoom"
    assert result["uid"] == "abc-123@example.com"


def test_parse_vevent_returns_none_when_no_summary():
    result = _parse_vevent("DTSTART:20260525T100000Z\nUID:x")
    assert result is None


def test_parse_vevent_returns_none_when_no_dtstart():
    result = _parse_vevent("SUMMARY:Meeting\nUID:x")
    assert result is None


def test_parse_vevent_end_is_none_when_missing():
    vevent = "SUMMARY:No end\nDTSTART:20260525T100000Z\nUID:y"
    result = _parse_vevent(vevent)
    assert result is not None
    assert result["end"] is None


# ── Fernet encryption round-trip ──────────────────────────────────────────────

def _make_fernet_key() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


def test_fernet_roundtrip():
    key = _make_fernet_key()
    data = {"username": "alice", "password": "secret123"}
    enc = _fernet_encrypt(data, key)
    dec = _fernet_decrypt(enc, key)
    assert dec == data


# ── CalDAVAdapter ─────────────────────────────────────────────────────────────

_CALDAV_RESPONSE = """<?xml version="1.0"?>
<multistatus>
  <response>
    <propstat>
      <prop>
        <calendar-data>BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-1@test
DTSTART:20260525T100000Z
DTEND:20260525T110000Z
SUMMARY:Sprint review
END:VEVENT
END:VCALENDAR
        </calendar-data>
      </prop>
    </propstat>
  </response>
</multistatus>"""


@pytest.mark.asyncio
async def test_caldav_adapter_parses_events():
    adapter = CalDAVAdapter("https://cal.example.com/cal", "user", "pass")

    class _FakeResponse:
        status_code = 207
        text = _CALDAV_RESPONSE

        def raise_for_status(self):
            pass

    async def _fake_request(*args, **kwargs):
        return _FakeResponse()

    with patch("httpx.AsyncClient.request", new=_fake_request):
        events = await adapter.fetch_events(days_ahead=7)

    assert len(events) == 1
    assert events[0]["summary"] == "Sprint review"
    assert "2026-05-25" in events[0]["start"]


@pytest.mark.asyncio
async def test_caldav_adapter_returns_empty_on_no_vevents():
    adapter = CalDAVAdapter("https://cal.example.com/cal", "user", "pass")

    class _FakeResponse:
        status_code = 207
        text = "<multistatus></multistatus>"

        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient.request", return_value=_FakeResponse()):
        events = await adapter.fetch_events()

    assert events == []


@pytest.mark.asyncio
async def test_caldav_adapter_raises_on_http_error():
    adapter = CalDAVAdapter("https://cal.example.com/cal", "user", "pass")

    class _FakeResponse:
        status_code = 401

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )

    with patch("httpx.AsyncClient.request", return_value=_FakeResponse()):
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fetch_events()


# ── GoogleCalendarAdapter ─────────────────────────────────────────────────────

_GOOGLE_EVENTS_RESPONSE = {
    "items": [
        {
            "id": "g-event-1",
            "summary": "Product demo",
            "start": {"dateTime": "2026-05-25T14:00:00Z"},
            "end": {"dateTime": "2026-05-25T15:00:00Z"},
            "description": "Show new features",
            "location": "Conference room A",
            "htmlLink": "https://calendar.google.com/event/1",
        },
        {
            "id": "g-event-2",
            "summary": "",  # should be filtered out
            "start": {"dateTime": "2026-05-25T16:00:00Z"},
            "end": {"dateTime": "2026-05-25T17:00:00Z"},
        },
    ]
}


@pytest.mark.asyncio
async def test_google_adapter_fetches_and_parses_events():
    adapter = GoogleCalendarAdapter(
        access_token="valid_token",
        refresh_token="refresh",
        client_id="client_id",
        client_secret="client_secret",
    )

    async def _fake_get(url, **kwargs):
        if "tokeninfo" in url:
            return MagicMock(status_code=200)
        if "events" in url:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=_GOOGLE_EVENTS_RESPONSE)
            return resp
        return MagicMock(status_code=200)

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        events = await adapter.fetch_events(days_ahead=7)

    # Only event with non-empty summary should be included
    assert len(events) == 1
    assert events[0]["summary"] == "Product demo"
    assert events[0]["uid"] == "g-event-1"


@pytest.mark.asyncio
async def test_google_adapter_refreshes_token_when_expired():
    adapter = GoogleCalendarAdapter(
        access_token="expired_token",
        refresh_token="valid_refresh",
        client_id="id",
        client_secret="secret",
    )

    call_log = []

    async def _fake_get(url, **kwargs):
        call_log.append(("get", url))
        if "tokeninfo" in url:
            return MagicMock(status_code=401)
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"items": []})
        return resp

    async def _fake_post(url, **kwargs):
        call_log.append(("post", url))
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"access_token": "new_token"})
        return resp

    with (
        patch.object(httpx.AsyncClient, "get", new=_fake_get),
        patch.object(httpx.AsyncClient, "post", new=_fake_post),
    ):
        events = await adapter.fetch_events()

    # Should have called tokeninfo → token refresh → events
    methods = [c[0] for c in call_log]
    assert "post" in methods  # refresh happened
    assert events == []


def test_google_adapter_auth_url_contains_client_id():
    url = GoogleCalendarAdapter.auth_url(
        client_id="my_client",
        redirect_uri="https://example.com/callback",
        state="random_state",
    )
    assert "my_client" in url
    assert "calendar.readonly" in url
    assert "random_state" in url


# ── MicrosoftGraphAdapter ─────────────────────────────────────────────────────

_MS_EVENTS_RESPONSE = {
    "value": [
        {
            "id": "ms-event-1",
            "subject": "Quarterly Review",
            "start": {"dateTime": "2026-05-26T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-05-26T11:00:00Z", "timeZone": "UTC"},
            "bodyPreview": "Q2 business review",
            "location": {"displayName": "Conference Room B"},
            "webLink": "https://outlook.office.com/event/1",
        },
        {
            "id": "ms-event-2",
            "subject": "",  # should be filtered out
            "start": {"dateTime": "2026-05-26T12:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-05-26T13:00:00Z", "timeZone": "UTC"},
        },
    ]
}


@pytest.mark.asyncio
async def test_ms_graph_adapter_fetches_and_parses_events():
    adapter = MicrosoftGraphAdapter(
        access_token="valid_ms_token",
        refresh_token="refresh_token",
        client_id="client_id",
        client_secret="client_secret",
    )

    async def _fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=_MS_EVENTS_RESPONSE)
        return resp

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        events = await adapter.fetch_events(days_ahead=7)

    assert len(events) == 1
    assert events[0]["summary"] == "Quarterly Review"
    assert events[0]["uid"] == "ms-event-1"
    assert events[0]["location"] == "Conference Room B"
    assert events[0]["html_link"] == "https://outlook.office.com/event/1"


@pytest.mark.asyncio
async def test_ms_graph_adapter_refreshes_token_on_401():
    adapter = MicrosoftGraphAdapter(
        access_token="expired_token",
        refresh_token="valid_refresh",
        client_id="id",
        client_secret="secret",
    )

    call_log = []

    async def _fake_get(url, **kwargs):
        call_log.append(kwargs.get("headers", {}).get("Authorization", ""))
        if "expired_token" in kwargs.get("headers", {}).get("Authorization", ""):
            resp = MagicMock()
            resp.status_code = 401
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value={})
            return resp
        # After refresh, new token
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"value": []})
        return resp

    async def _fake_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"access_token": "new_ms_token"})
        return resp

    with (
        patch.object(httpx.AsyncClient, "get", new=_fake_get),
        patch.object(httpx.AsyncClient, "post", new=_fake_post),
    ):
        events = await adapter.fetch_events()

    assert events == []
    # Should have tried twice (expired → refresh → retry)
    assert len(call_log) == 2


@pytest.mark.asyncio
async def test_ms_graph_adapter_raises_on_http_error():
    adapter = MicrosoftGraphAdapter(
        access_token="token",
        refresh_token="ref",
        client_id="id",
        client_secret="sec",
    )

    async def _fail_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 403

        def _raise():
            raise httpx.HTTPStatusError(
                "403 Forbidden",
                request=MagicMock(),
                response=MagicMock(status_code=403),
            )

        resp.raise_for_status = _raise
        return resp

    with patch.object(httpx.AsyncClient, "get", new=_fail_get):
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fetch_events()


def test_ms_graph_auth_url_contains_required_params():
    from app.services.calendar_sync import MicrosoftGraphAdapter

    url = MicrosoftGraphAdapter.auth_url(
        client_id="ms_client_id",
        redirect_uri="https://example.com/callback",
        state="state_xyz",
    )
    assert "ms_client_id" in url
    assert "Calendars.Read" in url
    assert "offline_access" in url
    assert "state_xyz" in url
    assert "login.microsoftonline.com" in url
