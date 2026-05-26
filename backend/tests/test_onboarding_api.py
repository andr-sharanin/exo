"""
E2E tests for Phase 5: /onboarding/* endpoints.
Uses the shared `client` fixture from conftest (rollback after each test).
"""
import uuid

import pytest
from httpx import AsyncClient

from app.services.onboarding import OnboardingMode, OnboardingService


def _quick_answers() -> list[dict]:
    """Build a valid complete answer set for quick mode."""
    questions = OnboardingService.get_questions(OnboardingMode.QUICK)
    return [
        {"question_id": q.question_id, "option_id": q.options[0].option_id}
        for q in questions
    ]


def _deep_answers() -> list[dict]:
    """Build a valid complete answer set for deep mode."""
    questions = OnboardingService.get_questions(OnboardingMode.DEEP)
    return [
        {"question_id": q.question_id, "option_id": q.options[0].option_id}
        for q in questions
    ]


class TestOnboardingStart:
    async def test_quick_start_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        assert r.status_code == 201

    async def test_deep_start_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/start", json={"mode": "deep"})
        assert r.status_code == 201

    async def test_start_returns_session_id_and_questions(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        data = r.json()
        assert "session_id" in data
        assert "questions" in data
        assert "total_questions" in data
        assert data["total_questions"] == len(data["questions"])
        assert data["total_questions"] == 7

    async def test_deep_mode_has_more_questions(self, client: AsyncClient) -> None:
        r_quick = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        r_deep = await client.post("/api/v1/onboarding/start", json={"mode": "deep"})
        assert r_deep.json()["total_questions"] > r_quick.json()["total_questions"]

    async def test_question_has_scenario_and_options(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        q = r.json()["questions"][0]
        assert "question_id" in q
        assert "scenario" in q
        assert "options" in q
        assert len(q["options"]) >= 2
        assert "option_id" in q["options"][0]
        assert "text" in q["options"][0]

    async def test_invalid_mode_returns_422(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/start", json={"mode": "turbo"})
        assert r.status_code == 422


class TestOnboardingSubmit:
    async def test_submit_quick_answers_returns_201(self, client: AsyncClient) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        session_id = start.json()["session_id"]
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id,
            "answers": _quick_answers(),
        })
        assert r.status_code == 201

    async def test_submit_returns_client_kernel_profile(self, client: AsyncClient) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        session_id = start.json()["session_id"]
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id,
            "answers": _quick_answers(),
        })
        data = r.json()
        assert "profile_data" in data
        assert "computed_defaults" in data
        assert "dominant_mode" in data["computed_defaults"]
        assert "recommended_session_length" in data["computed_defaults"]
        assert "calibration_version" in data

    async def test_submit_deep_mode_profile_has_all_nine_dimensions(
        self, client: AsyncClient
    ) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "deep"})
        session_id = start.json()["session_id"]
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id,
            "answers": _deep_answers(),
        })
        profile_data = r.json()["profile_data"]
        expected_dims = {
            "focus_stability", "task_handling_style", "decision_style",
            "overload_threshold", "interruption_behavior", "clarity_strategy",
            "execution_pattern", "help_seeking_behavior", "failure_response_pattern",
        }
        assert set(profile_data.keys()) == expected_dims

    async def test_submit_already_completed_session_returns_409(
        self, client: AsyncClient
    ) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        session_id = start.json()["session_id"]
        answers = _quick_answers()
        await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id, "answers": answers,
        })
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id, "answers": answers,
        })
        assert r.status_code == 409

    async def test_submit_unknown_session_returns_404(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": str(uuid.uuid4()),
            "answers": _quick_answers(),
        })
        assert r.status_code == 404

    async def test_submit_missing_questions_returns_422(self, client: AsyncClient) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        session_id = start.json()["session_id"]
        # Send only 3 of 7 answers
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id,
            "answers": _quick_answers()[:3],
        })
        assert r.status_code == 422

    async def test_submit_invalid_option_returns_422(self, client: AsyncClient) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        session_id = start.json()["session_id"]
        bad_answers = _quick_answers()
        bad_answers[0]["option_id"] = "INVALID"
        r = await client.post("/api/v1/onboarding/submit", json={
            "session_id": session_id,
            "answers": bad_answers,
        })
        assert r.status_code == 422


class TestOnboardingProfile:
    async def test_get_profile_before_onboarding_returns_404(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/onboarding/profile")
        assert r.status_code == 404

    async def test_get_profile_after_completion_returns_200(
        self, client: AsyncClient
    ) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        await client.post("/api/v1/onboarding/submit", json={
            "session_id": start.json()["session_id"],
            "answers": _quick_answers(),
        })
        r = await client.get("/api/v1/onboarding/profile")
        assert r.status_code == 200

    async def test_profile_contains_expected_fields(self, client: AsyncClient) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        await client.post("/api/v1/onboarding/submit", json={
            "session_id": start.json()["session_id"],
            "answers": _quick_answers(),
        })
        data = (await client.get("/api/v1/onboarding/profile")).json()
        assert "id" in data
        assert "profile_data" in data
        assert "computed_defaults" in data
        assert "calibration_version" in data
        assert data["calibration_version"] == 1


class TestOnboardingRecalibrate:
    async def test_recalibrate_without_prior_profile_returns_404(
        self, client: AsyncClient
    ) -> None:
        r = await client.post("/api/v1/onboarding/recalibrate")
        assert r.status_code == 404

    async def test_recalibrate_returns_updated_profile(
        self, client: AsyncClient
    ) -> None:
        start = await client.post("/api/v1/onboarding/start", json={"mode": "quick"})
        await client.post("/api/v1/onboarding/submit", json={
            "session_id": start.json()["session_id"],
            "answers": _quick_answers(),
        })
        r = await client.post("/api/v1/onboarding/recalibrate")
        assert r.status_code == 201
        data = r.json()
        assert "computed_defaults" in data
        assert "dominant_mode" in data["computed_defaults"]
