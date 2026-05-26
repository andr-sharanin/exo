"""
Telegram Bot v2 — FSM-driven conversational interface.

POST /telegram/webhook    — receives Telegram Update objects
GET  /telegram/link-token — (authenticated) generate a one-time link token

Commands:
  /start           → welcome + link instructions
  /link <token>    → link Telegram account to ExoCortex user
  /capture <text>  → create a new Command (captured task)
  /energy          → multi-step energy check-in via inline buttons
  /plan            → show today's plan summary
  /habits          → list habits with one-tap checkin buttons
  /status          → current energy + brief status

FSM states (stored in Redis tg:state:{chat_id}):
  idle
  energy_sleep   → waiting for sleep quality (1-5)
  energy_mood    → waiting for mood (1-5)
  energy_energy  → waiting for energy level (1-5)
"""
import uuid
from datetime import date, datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.sse import get_redis_pool
from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.telegram_user import TelegramUser
from app.services.config_service import ConfigService
from app.services.telegram_bot import (
    answer_callback,
    clear_state,
    consume_link_token,
    create_link_token,
    edit_message_text,
    get_state,
    inline_keyboard,
    send_message,
    set_state,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_redis_pool(), decode_responses=True)


async def _get_bot_token() -> str | None:
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        svc = ConfigService(db)
        return await svc.get("telegram_bot_token")


async def _get_tg_user(chat_id: int, db) -> TelegramUser | None:
    q = select(TelegramUser).where(TelegramUser.telegram_chat_id == chat_id)
    return (await db.execute(q)).scalar_one_or_none()


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram Update. Always returns 200 to prevent Telegram retry loops."""
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    bot_token = await _get_bot_token()
    if not bot_token:
        return {"ok": True}

    r = _redis()

    # ── Callback query (inline button press) ─────────────────────────────────
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        data = cq.get("data", "")
        await answer_callback(bot_token, cq["id"])
        await _handle_callback(bot_token, r, chat_id, message_id, data)
        return {"ok": True}

    # ── Regular message ───────────────────────────────────────────────────────
    message = update.get("message", {})
    chat_id: int = message.get("chat", {}).get("id")
    text: str = message.get("text", "").strip()
    username: str | None = message.get("from", {}).get("username")

    if not chat_id or not text:
        return {"ok": True}

    await _handle_message(bot_token, r, chat_id, text, username)
    return {"ok": True}


async def _handle_message(
    bot_token: str, r, chat_id: int, text: str, username: str | None
) -> None:
    from app.core.database import AsyncSessionLocal

    # ── /start ────────────────────────────────────────────────────────────────
    if text.startswith("/start"):
        await clear_state(r, chat_id)
        await send_message(
            bot_token, chat_id,
            "👋 <b>ExoCortex Bot</b>\n\n"
            "Для работы свяжи Telegram с аккаунтом:\n"
            "1. Открой ExoCortex → Аккаунт → «Связать Telegram»\n"
            "2. Скопируй токен и отправь сюда: <code>/link &lt;token&gt;</code>\n\n"
            "После привязки: /help — список команд"
        )
        return

    # ── /link <token> ─────────────────────────────────────────────────────────
    if text.startswith("/link "):
        token = text[len("/link "):].strip()
        payload = await consume_link_token(r, token)
        if not payload:
            await send_message(bot_token, chat_id,
                               "❌ Токен недействителен или истёк. Создай новый в веб-приложении.")
            return
        async with AsyncSessionLocal() as db:
            existing = await _get_tg_user(chat_id, db)
            if existing:
                existing.telegram_username = username
                existing.user_id = uuid.UUID(payload["user_id"])
                existing.tenant_id = uuid.UUID(payload["tenant_id"])
            else:
                db.add(TelegramUser(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(payload["tenant_id"]),
                    user_id=uuid.UUID(payload["user_id"]),
                    telegram_chat_id=chat_id,
                    telegram_username=username,
                ))
            await db.commit()
        await send_message(bot_token, chat_id,
                           "✅ <b>Аккаунт привязан!</b>\n\n"
                           "/capture — захватить задачу\n"
                           "/energy — проверка энергии\n"
                           "/plan — план дня\n"
                           "/habits — привычки\n"
                           "/status — текущий статус")
        return

    # ── All commands below require linked account ─────────────────────────────
    async with AsyncSessionLocal() as db:
        tg_user = await _get_tg_user(chat_id, db)
        if not tg_user:
            await send_message(bot_token, chat_id,
                               "⚠️ Сначала свяжи аккаунт: /start")
            return

        if text.startswith("/capture "):
            await _cmd_capture(bot_token, r, db, chat_id, text[9:].strip(), tg_user)
        elif text == "/energy":
            await _cmd_energy_start(bot_token, r, chat_id)
        elif text == "/plan":
            await _cmd_plan(bot_token, db, chat_id, tg_user)
        elif text == "/habits":
            await _cmd_habits(bot_token, db, chat_id, tg_user)
        elif text == "/status":
            await _cmd_status(bot_token, db, chat_id, tg_user)
        elif text == "/help":
            await send_message(bot_token, chat_id,
                               "/capture <текст> — захватить задачу\n"
                               "/energy — check-in энергии\n"
                               "/plan — план дня\n"
                               "/habits — привычки\n"
                               "/status — текущий статус")
        else:
            # Check FSM state — maybe user typed a value mid-flow
            state = await get_state(r, chat_id)
            if state["state"] != "idle":
                await _handle_fsm_text(bot_token, r, db, chat_id, text, tg_user, state)


async def _handle_callback(
    bot_token: str, r, chat_id: int, message_id: int, data: str
) -> None:
    """Handle inline button callbacks (energy steps, habit checkins)."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        tg_user = await _get_tg_user(chat_id, db)
        if not tg_user:
            return

        if data.startswith("energy:"):
            await _cb_energy(bot_token, r, db, chat_id, message_id, data, tg_user)
        elif data.startswith("habit_done:"):
            await _cb_habit_done(bot_token, r, db, chat_id, message_id, data, tg_user)


# ── Command handlers ──────────────────────────────────────────────────────────

async def _cmd_capture(bot_token, r, db, chat_id, text, tg_user) -> None:
    from app.models.command import Command
    from arq import create_pool
    from arq.connections import RedisSettings
    from app.core.config import settings as app_settings

    idem_key = f"tg-{chat_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    cmd_id = uuid.uuid4()
    cmd = Command(
        id=cmd_id,
        tenant_id=tg_user.tenant_id,
        user_id=tg_user.user_id,
        raw_payload_ref=text[:500],
        raw_input=text[:500],
        ingress_channel="telegram",
        ingress_modality="text",
        idempotency_key=idem_key,
        status="pending",
        kernel_status="pending_analysis",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(cmd)
    await db.commit()

    # Enqueue kernel analysis (same as web capture)
    try:
        arq = await create_pool(RedisSettings.from_dsn(app_settings.REDIS_URL))
        await arq.enqueue_job(
            "analyze_command_task",
            str(cmd_id),
            str(tg_user.user_id),
            str(tg_user.tenant_id),
            text[:500],
        )
    except Exception:
        pass  # Analysis will run when worker picks it up

    await send_message(bot_token, chat_id,
                       f"✅ Захвачено: <i>{text[:200]}</i>\n\n"
                       "AI проанализирует через секунды — проверь в Inbox.")


async def _cmd_energy_start(bot_token, r, chat_id) -> None:
    await set_state(r, chat_id, "energy_sleep")
    kb = inline_keyboard([[
        ("😴 1", "energy:sleep:1"), ("😐 2", "energy:sleep:2"),
        ("🙂 3", "energy:sleep:3"), ("😊 4", "energy:sleep:4"),
        ("🤩 5", "energy:sleep:5"),
    ]])
    await send_message(bot_token, chat_id,
                       "⚡ <b>Проверка энергии</b>\n\n"
                       "Как ты спал? (1 — плохо, 5 — отлично)",
                       reply_markup=kb)


async def _cmd_plan(bot_token, db, chat_id, tg_user) -> None:
    from app.repositories.secretary_repos import DayPlanRepo
    plan = await DayPlanRepo(db).get_today_for_tenant(tg_user.tenant_id)
    if not plan:
        await send_message(bot_token, chat_id,
                           "📋 Плана на сегодня нет.\n"
                           "Открой ExoCortex и сгенерируй план.")
        return
    lines = [f"📋 <b>План на {plan.plan_date}</b> [{plan.status}]"]
    for item in plan.items[:8]:
        t = f"{item['estimated_minutes']}м" if item.get("estimated_minutes") else "—"
        lines.append(f"{item['order']}. {item['title']} ({t})")
    if len(plan.items) > 8:
        lines.append(f"... и ещё {len(plan.items) - 8}")
    await send_message(bot_token, chat_id, "\n".join(lines))


async def _cmd_habits(bot_token, db, chat_id, tg_user) -> None:
    from app.models.habit import HabitDefinition, HabitEntry
    from sqlalchemy import func as sqlfunc
    today = date.today()
    q = select(HabitDefinition).where(
        HabitDefinition.user_id == tg_user.user_id,
        HabitDefinition.is_active == True,  # noqa: E712
    )
    habits = list((await db.execute(q)).scalars().all())
    if not habits:
        await send_message(bot_token, chat_id, "🔁 Нет активных привычек.")
        return

    lines = ["🔁 <b>Привычки сегодня</b>"]
    rows = []
    for h in habits[:6]:
        done_q = select(HabitEntry).where(
            HabitEntry.habit_id == h.id,
            sqlfunc.date(HabitEntry.completed_at) == today,
        )
        done = (await db.execute(done_q)).scalar_one_or_none() is not None
        mark = "✅" if done else "⬜"
        lines.append(f"{mark} {h.title}")
        if not done:
            rows.append([(f"✓ {h.title[:20]}", f"habit_done:{h.id}")])

    kb = inline_keyboard(rows) if rows else None
    kwargs = {"reply_markup": kb} if kb else {}
    await send_message(bot_token, chat_id, "\n".join(lines), **kwargs)


async def _cmd_status(bot_token, db, chat_id, tg_user) -> None:
    from app.repositories.energy_repos import EnergyScoreRepo, SystemModeRepo
    energy = await EnergyScoreRepo(db).get_latest(tg_user.tenant_id, tg_user.user_id)
    mode = await SystemModeRepo(db).get_current(tg_user.tenant_id, tg_user.user_id)
    state_emoji = {"sufficient": "🟢", "constrained": "🟡", "critical": "🔴"}
    e_text = (
        f"{state_emoji.get(energy.state, '❓')} <b>Энергия:</b> {energy.score}/100 ({energy.state})"
        if energy else "⚡ Энергия: нет данных"
    )
    m_text = f"🔄 <b>Режим:</b> {mode.mode}" if mode else "🔄 Режим: harmony (по умолчанию)"
    await send_message(bot_token, chat_id, f"{e_text}\n{m_text}")


# ── FSM: energy check-in callbacks ───────────────────────────────────────────

async def _cb_energy(bot_token, r, db, chat_id, message_id, data, tg_user) -> None:
    """data format: energy:step:value  e.g. energy:sleep:3"""
    _, step, value_str = data.split(":")
    value = int(value_str)
    state = await get_state(r, chat_id)
    fsm_data = state.get("data", {})
    fsm_data[step] = value

    if step == "sleep":
        await set_state(r, chat_id, "energy_mood", fsm_data)
        kb = inline_keyboard([[
            ("😞 1", "energy:mood:1"), ("😐 2", "energy:mood:2"),
            ("🙂 3", "energy:mood:3"), ("😊 4", "energy:mood:4"),
            ("🤩 5", "energy:mood:5"),
        ]])
        await edit_message_text(bot_token, chat_id, message_id,
                                f"Сон: {value}/5 ✓\n\nКаково настроение?",
                                reply_markup=kb)

    elif step == "mood":
        await set_state(r, chat_id, "energy_energy", fsm_data)
        kb = inline_keyboard([[
            ("🪫 1", "energy:energy:1"), ("😴 2", "energy:energy:2"),
            ("🙂 3", "energy:energy:3"), ("⚡ 4", "energy:energy:4"),
            ("🚀 5", "energy:energy:5"),
        ]])
        await edit_message_text(bot_token, chat_id, message_id,
                                f"Сон: {fsm_data['sleep']}/5 ✓\nНастроение: {value}/5 ✓\n\nКакой уровень энергии?",
                                reply_markup=kb)

    elif step == "energy":
        # Submit check-in
        await clear_state(r, chat_id)
        from app.models.energy_score import EnergyScore
        from app.repositories.energy_repos import EnergyScoreRepo
        from app.services.energy import EnergyScoreEngine
        score = EnergyScoreEngine.compute_from_checkin(
            sleep=fsm_data.get("sleep", 3),
            mood=fsm_data.get("mood", 3),
            energy=value,
        )
        prev = await EnergyScoreRepo(db).get_latest(tg_user.tenant_id, tg_user.user_id)
        from app.services.energy import EnergyState
        prev_state = EnergyState(prev.state) if prev else None
        energy_state = EnergyScoreEngine.compute_state(score, prev_state)
        from datetime import timedelta
        new_score = EnergyScore(
            id=uuid.uuid4(),
            tenant_id=tg_user.tenant_id,
            user_id=tg_user.user_id,
            score=score,
            state=energy_state,
            is_override=False,
            valid_until=datetime.now(timezone.utc) + timedelta(hours=12),
            checkin_signals={
                "sleep_quality": fsm_data.get("sleep", 3),
                "mood": fsm_data.get("mood", 3),
                "energy_level": value,
            },
        )
        db.add(new_score)
        await db.commit()
        state_emoji = {"sufficient": "🟢", "constrained": "🟡", "critical": "🔴"}
        emoji = state_emoji.get(energy_state, "❓")
        await edit_message_text(
            bot_token, chat_id, message_id,
            f"✅ <b>Check-in сохранён</b>\n\n"
            f"{emoji} Энергия: {score}/100 ({energy_state})\n\n"
            f"Сон: {fsm_data['sleep']}/5 | Настроение: {fsm_data['mood']}/5 | Энергия: {value}/5"
        )


async def _cb_habit_done(bot_token, r, db, chat_id, message_id, data, tg_user) -> None:
    """data format: habit_done:{habit_id}"""
    habit_id_str = data.split(":", 1)[1]
    habit_id = uuid.UUID(habit_id_str)
    today = date.today()

    from app.models.habit import HabitDefinition, HabitEntry
    from sqlalchemy import func as sqlfunc

    # Idempotency check
    existing = (await db.execute(
        select(HabitEntry).where(
            HabitEntry.habit_id == habit_id,
            sqlfunc.date(HabitEntry.completed_at) == today,
        )
    )).scalar_one_or_none()

    if existing:
        await edit_message_text(bot_token, chat_id, message_id,
                                "✅ Привычка уже отмечена сегодня.")
        return

    habit = (await db.execute(
        select(HabitDefinition).where(HabitDefinition.id == habit_id)
    )).scalar_one_or_none()

    entry = HabitEntry(
        id=uuid.uuid4(),
        tenant_id=tg_user.tenant_id,
        user_id=tg_user.user_id,
        habit_id=habit_id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()

    name = habit.title if habit else habit_id_str
    await edit_message_text(bot_token, chat_id, message_id,
                            f"✅ <b>{name}</b> — отмечено!")


async def _handle_fsm_text(bot_token, r, db, chat_id, text, tg_user, state) -> None:
    """Handles free-text input during an active FSM flow."""
    # Currently only energy flow uses buttons; no text-based FSM states
    await clear_state(r, chat_id)
    await send_message(bot_token, chat_id,
                       "Используй кнопки для ввода. Начни заново: /energy")


# ── Link token endpoint (authenticated web user) ──────────────────────────────

@router.get("/link-token")
async def get_link_token(user: CurrentUser) -> dict:
    """
    Returns a one-time token that the user can send to the Telegram bot via /link <token>.
    Token expires in 10 minutes.
    """
    r = _redis()
    token = await create_link_token(r, str(user.user_id), str(user.tenant_id))
    return {
        "token": token,
        "expires_in_seconds": 600,
        "instruction": f"Send to bot: /link {token}",
    }
