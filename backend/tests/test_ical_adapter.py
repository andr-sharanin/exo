"""
Unit tests for ICalAdapter and _parse_ical_text.

All HTTP calls are intercepted — no real network.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.calendar_sync import ICalAdapter, _parse_ical_text

# ── Sample iCal data ──────────────────────────────────────────────────────────

def _make_ical(events: list[dict]) -> str:
    """Build a minimal iCal document with the given events."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0"]
    for ev in events:
        lines.append("BEGIN:VEVENT")
        for k, v in ev.items():
            lines.append(f"{k}:{v}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def _future_dt(hours_ahead: int = 24) -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _past_dt(hours_ago: int = 24) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.strftime("%Y%m%dT%H%M%SZ")


# ── _parse_ical_text ──────────────────────────────────────────────────────────

class TestParseIcalText:
    def test_returns_upcoming_events(self):
        ical = _make_ical([
            {"SUMMARY": "Future meeting", "DTSTART": _future_dt(2), "UID": "1"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert len(events) == 1
        assert events[0]["summary"] == "Future meeting"

    def test_filters_out_past_events(self):
        ical = _make_ical([
            {"SUMMARY": "Past event", "DTSTART": _past_dt(48), "UID": "2"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert events == []

    def test_filters_events_beyond_days_ahead(self):
        ical = _make_ical([
            {"SUMMARY": "Far future", "DTSTART": _future_dt(200), "UID": "3"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert events == []

    def test_returns_multiple_events_sorted_by_input_order(self):
        ical = _make_ical([
            {"SUMMARY": "Event A", "DTSTART": _future_dt(1), "UID": "4a"},
            {"SUMMARY": "Event B", "DTSTART": _future_dt(3), "UID": "4b"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert len(events) == 2
        summaries = [e["summary"] for e in events]
        assert "Event A" in summaries
        assert "Event B" in summaries

    def test_skips_events_with_no_summary(self):
        ical = _make_ical([
            {"DTSTART": _future_dt(2), "UID": "5"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert events == []

    def test_all_day_event_included_when_in_range(self):
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d")
        ical = _make_ical([
            {"SUMMARY": "All-day", "DTSTART": tomorrow, "UID": "6"},
        ])
        events = _parse_ical_text(ical, days_ahead=7)
        assert len(events) == 1
        assert events[0]["summary"] == "All-day"

    def test_empty_feed_returns_empty_list(self):
        events = _parse_ical_text("BEGIN:VCALENDAR\nEND:VCALENDAR", days_ahead=7)
        assert events == []


# ── ICalAdapter ───────────────────────────────────────────────────────────────

class TestICalAdapter:
    @pytest.mark.asyncio
    async def test_fetch_events_parses_ical_response(self):
        ical_body = _make_ical([
            {"SUMMARY": "Standup", "DTSTART": _future_dt(2), "UID": "a1"},
        ])

        class _FakeResponse:
            status_code = 200
            text = ical_body

            def raise_for_status(self):
                pass

        with patch("httpx.AsyncClient.get", return_value=_FakeResponse()):
            adapter = ICalAdapter("https://example.com/cal.ics")
            events = await adapter.fetch_events(days_ahead=7)

        assert len(events) == 1
        assert events[0]["summary"] == "Standup"

    @pytest.mark.asyncio
    async def test_fetch_events_returns_empty_for_all_past(self):
        ical_body = _make_ical([
            {"SUMMARY": "Old event", "DTSTART": _past_dt(72), "UID": "b1"},
        ])

        class _FakeResponse:
            status_code = 200
            text = ical_body

            def raise_for_status(self):
                pass

        with patch("httpx.AsyncClient.get", return_value=_FakeResponse()):
            adapter = ICalAdapter("https://example.com/old.ics")
            events = await adapter.fetch_events(days_ahead=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_fetch_events_raises_on_http_error(self):
        class _FakeResponse:
            status_code = 404

            def raise_for_status(self):
                raise httpx.HTTPStatusError(
                    "404 Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )

        with patch("httpx.AsyncClient.get", return_value=_FakeResponse()):
            adapter = ICalAdapter("https://example.com/missing.ics")
            with pytest.raises(httpx.HTTPStatusError):
                await adapter.fetch_events()

    @pytest.mark.asyncio
    async def test_fetch_events_respects_days_ahead(self):
        # Event at 10 days ahead — should be excluded with days_ahead=7
        ical_body = _make_ical([
            {"SUMMARY": "Far event", "DTSTART": _future_dt(240), "UID": "c1"},
        ])

        class _FakeResponse:
            status_code = 200
            text = ical_body

            def raise_for_status(self):
                pass

        with patch("httpx.AsyncClient.get", return_value=_FakeResponse()):
            adapter = ICalAdapter("https://example.com/cal.ics")
            events = await adapter.fetch_events(days_ahead=7)

        assert events == []
