"""
Phase 6 — AI Layer endpoints.

POST /ai/classify  — Tier 1 (Mechanical): intent + urgency + complexity
POST /ai/reason    — Tier 1–3 (routed by complexity + energy): full reasoning
POST /ai/advisory  — Tier 2 (Analytical): executive-function advice
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.ai_request_log import AIRequestLog
from app.repositories.ai_repos import AIRequestLogRepo
from app.schemas.ai_schemas import (
    AdvisoryRequest,
    AdvisoryResponse,
    ClassifyRequest,
    ClassifyResponse,
    ReasonRequest,
    ReasonResponse,
)
from app.services import audit
from app.services.ai_client import AIClient, AIClientError
from app.services.ai_router import AIRouter, AIRoutingContext, PipelineStage

router = APIRouter(prefix="/ai", tags=["ai"])

# ── Prompt templates ──────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = (
    "You are an intent classifier. Respond only with valid JSON.\n"
    'Classify the input and return: {"intent_class": "task|question|idea|noise", '
    '"urgency": "low|medium|high", "complexity": "low|medium|high", '
    '"confidence": <float 0.0-1.0>}'
)

_REASON_SYSTEM = (
    "You are an executive function assistant. Respond only with valid JSON.\n"
    "Analyse the input and return: "
    '{"intent_hypothesis": "<what the user wants to achieve>", '
    '"ambiguity_level": "none|low|medium|high", '
    '"actionability_status": "actionable|needs_clarification|non_actionable|defer_candidate", '
    '"reasoning": "<brief explanation>"}'
)

_ADVISORY_SYSTEM_TPL = (
    "You are an executive function coach. Respond only with valid JSON.\n"
    "User energy: {energy_state}. System mode: {system_mode}.\n"
    'Return: {"response": "<concise advice>", '
    '"suggestions": ["<action 1>", "<action 2>", "<action 3>"], '
    '"confidence": <float 0.0-1.0>}'
)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _log_request(
    db: TenantDB,
    user: CurrentUser,
    *,
    stage: str,
    ai_response,
    request_id: uuid.UUID,
) -> None:
    log = AIRequestLog(
        id=request_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        stage=stage,
        tier=ai_response.tier,
        model_used=ai_response.model_used,
        status="success",
        prompt_tokens=ai_response.prompt_tokens,
        completion_tokens=ai_response.completion_tokens,
        latency_ms=ai_response.latency_ms,
        was_fallback=ai_response.was_fallback,
    )
    await AIRequestLogRepo(db).create(log)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/classify",
    response_model=ClassifyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def classify(
    body: ClassifyRequest,
    db: TenantDB,
    user: CurrentUser,
) -> ClassifyResponse:
    ctx = AIRoutingContext(stage=PipelineStage.CLASSIFICATION)
    config = AIRouter.route(ctx)

    messages = [
        {"role": "system", "content": _CLASSIFY_SYSTEM},
        {"role": "user", "content": f"Input: {body.text}"},
    ]

    try:
        ai = await AIClient.complete(messages, config)
    except AIClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    request_id = uuid.uuid4()
    await _log_request(db, user, stage="classification", ai_response=ai, request_id=request_id)

    p = ai.parsed
    return ClassifyResponse(
        request_id=request_id,
        tier=ai.tier,
        model_used=ai.model_used,
        intent_class=p.get("intent_class", "task"),
        urgency=p.get("urgency", "medium"),
        complexity=p.get("complexity", "medium"),
        confidence=float(p.get("confidence", 0.5)),
        prompt_tokens=ai.prompt_tokens,
        completion_tokens=ai.completion_tokens,
        latency_ms=ai.latency_ms,
        was_fallback=ai.was_fallback,
    )


@router.post(
    "/reason",
    response_model=ReasonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reason(
    body: ReasonRequest,
    db: TenantDB,
    user: CurrentUser,
) -> ReasonResponse:
    ctx = AIRoutingContext(
        stage=PipelineStage.REASON,
        complexity=body.complexity,
        energy_state=body.energy_state,
    )
    config = AIRouter.route(ctx)

    messages = [
        {"role": "system", "content": _REASON_SYSTEM},
        {"role": "user", "content": f"Text: {body.text}\nIntent class: {body.intent_class}"},
    ]

    try:
        ai = await AIClient.complete(messages, config)
    except AIClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    request_id = uuid.uuid4()
    await _log_request(db, user, stage="reason", ai_response=ai, request_id=request_id)

    p = ai.parsed
    return ReasonResponse(
        request_id=request_id,
        tier=ai.tier,
        model_used=ai.model_used,
        intent_hypothesis=p.get("intent_hypothesis", ""),
        ambiguity_level=p.get("ambiguity_level", "medium"),
        actionability_status=p.get("actionability_status", "needs_clarification"),
        reasoning=p.get("reasoning", ""),
        prompt_tokens=ai.prompt_tokens,
        completion_tokens=ai.completion_tokens,
        latency_ms=ai.latency_ms,
        was_fallback=ai.was_fallback,
    )


@router.post(
    "/advisory",
    response_model=AdvisoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def advisory(
    body: AdvisoryRequest,
    db: TenantDB,
    user: CurrentUser,
) -> AdvisoryResponse:
    ctx = AIRoutingContext(
        stage=PipelineStage.ADVISORY,
        energy_state=body.energy_state,
        system_mode=body.system_mode,
    )
    config = AIRouter.route(ctx)

    system_prompt = _ADVISORY_SYSTEM_TPL.format(
        energy_state=body.energy_state,
        system_mode=body.system_mode,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Query: {body.query}"},
    ]

    try:
        ai = await AIClient.complete(messages, config)
    except AIClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    request_id = uuid.uuid4()
    await _log_request(db, user, stage="advisory", ai_response=ai, request_id=request_id)

    p = ai.parsed
    return AdvisoryResponse(
        request_id=request_id,
        tier=ai.tier,
        model_used=ai.model_used,
        response=p.get("response", ""),
        suggestions=p.get("suggestions", []),
        confidence=float(p.get("confidence", 0.5)),
        prompt_tokens=ai.prompt_tokens,
        completion_tokens=ai.completion_tokens,
        latency_ms=ai.latency_ms,
        was_fallback=ai.was_fallback,
    )
