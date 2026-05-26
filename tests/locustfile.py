"""Locust load test — target: 500 concurrent users, p95 < 500ms.

Usage:
    locust -f tests/locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 50

Set EXOCORTEX_TOKEN env var to a valid Keycloak access token before running.
Generate one:
    curl -s -X POST http://localhost:8080/realms/exocortex/protocol/openid-connect/token \
      -d "client_id=exocortex-api&grant_type=password&username=USER&password=PASS" \
      | jq -r .access_token
"""
import os
from locust import HttpUser, task, between

_TOKEN = os.getenv("EXOCORTEX_TOKEN", "")


class ExoCortexUser(HttpUser):
    wait_time = between(0.3, 1.5)

    def on_start(self) -> None:
        self.auth = {"Authorization": f"Bearer {_TOKEN}"}

    # ── Unauthenticated ───────────────────────────────────────────────────────

    @task(5)
    def health(self) -> None:
        self.client.get("/api/v1/health", name="/health")

    # ── Read-heavy (auth required) ────────────────────────────────────────────

    @task(10)
    def energy_score(self) -> None:
        self.client.get("/api/v1/energy/score", headers=self.auth, name="/energy/score")

    @task(8)
    def today_plan(self) -> None:
        self.client.get(
            "/api/v1/secretary/plan/today",
            headers=self.auth,
            name="/secretary/plan/today",
        )

    @task(6)
    def list_goals(self) -> None:
        self.client.get(
            "/api/v1/planning/goals?horizon=daily",
            headers=self.auth,
            name="/planning/goals",
        )

    @task(4)
    def list_deposits(self) -> None:
        self.client.get("/api/v1/deposits", headers=self.auth, name="/deposits")

    # ── Write operations ──────────────────────────────────────────────────────

    @task(3)
    def capture_command(self) -> None:
        self.client.post(
            "/api/v1/commands",
            json={"raw_input": "load test task — please process"},
            headers=self.auth,
            name="/commands POST",
        )

    @task(2)
    def energy_checkin(self) -> None:
        self.client.post(
            "/api/v1/energy/checkin",
            json={"sleep_score": 7, "mood_score": 6, "energy_score": 7},
            headers=self.auth,
            name="/energy/checkin POST",
        )
