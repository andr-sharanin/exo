from fastapi import APIRouter

from app.api.v1 import (
    health,
    commands,
    users,
    calendar,
    governance,
    subscriptions,
    team,
    capture,
    reason,
    decide,
    schedule,
    steps,
    sessions,
    witness,
    outcomes,
    transitions,
    behavioral_events,
    energy,
    modes,
    onboarding,
    ai,
    admin,
    secretary,
    agents,
    planning,
    deposits,
    config,
    telegram,
    push,
    stripe_webhook,
    sse,
    reviews,
    habits,
    admin_agents,
    brief,
)

router = APIRouter()

# System
router.include_router(health.router, tags=["system"])

# Pipeline stages (in canonical order)
router.include_router(commands.router)
router.include_router(capture.router)
router.include_router(reason.router)
router.include_router(decide.router)
router.include_router(schedule.router)
router.include_router(steps.router)
router.include_router(sessions.router)
router.include_router(witness.router)
router.include_router(outcomes.router)

# Generic FSM transition (all objects)
router.include_router(transitions.router)

# Behavioral layer
router.include_router(behavioral_events.router)

# Phase 4 — Energy & Mode
router.include_router(energy.router)
router.include_router(modes.router)

# Phase 5 — Onboarding & Kernel Calibration
router.include_router(onboarding.router)

# Phase 6 — AI Layer & Admin Panel
router.include_router(ai.router)
router.include_router(admin.router)

# Phase 7 — Secretary & Agent System
router.include_router(secretary.router)
router.include_router(agents.router)

# Phase 8 — Planning Horizons & Deposit
router.include_router(planning.router)
router.include_router(deposits.router)

# Phase 9 — System Configuration + Integrations
router.include_router(config.router)
router.include_router(telegram.router)
router.include_router(push.router)
router.include_router(stripe_webhook.router)

# Phase 13 — Real-time SSE
router.include_router(sse.router)

# Phase 14 — Policy Kernel + Reviews (планёрки)
router.include_router(reviews.router)

# Phase 16 — Habits + Dynamic Agents Admin
router.include_router(habits.router)
router.include_router(admin_agents.router)

# Morning Brief
router.include_router(brief.router)

# GDPR — user data export + account deletion
router.include_router(users.router)

# Governance ADR
router.include_router(governance.router)

# Calendar sync (CalDAV + Google Calendar + Microsoft Graph)
router.include_router(calendar.router)

# Subscriptions / tiers
router.include_router(subscriptions.router)

# Team management (Team tier only)
router.include_router(team.router)
