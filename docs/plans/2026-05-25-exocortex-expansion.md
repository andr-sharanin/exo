# ExoCortex — Expansion Implementation Plan
# Phases 13–20: From MVP to Mature Product

> **For agentic workers:** Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Transform ExoCortex from a working MVP into a mature, ambient intelligence system that users return to daily and that handles production load reliably.

**Architecture:** Event-driven background processing foundation → rich UI layer → external integrations → robustness hardening.

**Tech Stack additions:** ARQ (Redis job queue), SSE (Server-Sent Events), Whisper (voice), Gmail API, Tenacity (circuit breaker), Sentry, Redis caching layer.

---

## ЧАСТЬ 0 — ЧТО МЫ ВЫПУСТИЛИ ИЗ ВИДА

### Критические пробелы в пользовательской ценности

**0.1 — Фоновая обработка (ARQ)**
Все AI-вызовы сейчас синхронны в request-response цикле. Пользователь ждёт 10–15 секунд на генерацию плана. Если Anthropic тормозит — 504. Нет возможности делать проактивную работу (утренний brief до того как пользователь открыл приложение). Это ФУНДАМЕНТ — без него всё остальное не работает хорошо.

**0.2 — Реальное время (SSE)**
Дашборд — статический server render. Пришло новое Telegram-сообщение — надо обновить страницу вручную. В 2026 году это неприемлемо.

**0.3 — Привычки (Habits)**
Таблицы `habit_definitions` и `habit_entries` есть. UI нет. Привычки — это то, что возвращает пользователя ЕЖЕДНЕВНО. Без них retention критически низкий.

**0.4 — Telegram-бот как основной мобильный интерфейс**
Telegram уже стоит на телефоне. Telegram уже доверяют уведомлениям. Голосовые сообщения → Whisper → capture работает лучше чем любой мобильный UI. Сейчас бот — заглушка.

**0.5 — Еженедельный ретроспектив**
"Reflect" стадия в пайплайне есть. UI для недельного обзора нет. Weekly review — самая ценная продуктивность-привычка по всем исследованиям.

**0.6 — Поиск**
После 3 месяцев использования: 500+ captures, 100+ целей, 1000+ задач. Без поиска пользователь полностью теряется в своих же данных.

**0.7 — Task CRUD + Inbox**
Пользователь не может ВИДЕТЬ свои задачи, редактировать, удалять, вручную добавлять в план. Система генерирует план "из воздуха" — пользователь не контролирует входные данные.

**0.8 — Onboarding**
Endpoints есть, UI нет. Пользователь попадает на дашборд и не понимает с чего начать. Первые 5 минут определяют останется ли он навсегда.

### Критические пробелы в надёжности ПО

**0.9 — Нет индексов БД**
22 таблицы, у всех `user_id UUID` + `created_at`. Без индексов запросы с фильтрами будут полные seq scans. При 1000 пользователей — катастрофа.

**0.10 — Нет кэширования (Redis)**
Energy score при каждом запросе к дашборду — запрос к БД. Plan generation — 5+ запросов к БД. Всё это кэшируется тривиально.

**0.11 — Нет circuit breaker для AI**
Anthropic лежит → все запросы зависают → pool connection exhaustion → сервис падает. Нужен Tenacity + fallback.

**0.12 — Нет error monitoring**
Grafana показывает метрики, но не исключения со stack trace. Production баги невидимы.

**0.13 — Нет pagination**
GET /goals, GET /commands — без limit/offset. При 1000 записях — OOM.

**0.14 — Нет стратегии ротации EXOCORTEX_SECRET_KEY**
Если ключ скомпрометирован — нет процедуры миграции зашифрованных данных на новый ключ.

**0.15 — Нет GDPR data export**
Для европейских пользователей — юридическое требование.

### Три вещи, которые никто не упомянул

**0.16 — "Promise extraction" из сообщений**
AI читает твои ИСХОДЯЩИЕ сообщения и извлекает обязательства. Написал "пришлю отчёт до пятницы" → автоматически создаётся задача с дедлайном пятница. Полностью невидимо, пока не нужно.

**0.17 — Energy pattern learning**
После 30 check-ins система знает паттерны. Понедельник утром — всегда низко? Система спрашивает: "Ожидаю 38/100 сегодня, на основе 8 предыдущих понедельников — подтверди или скорректируй". Check-in занимает 5 секунд вместо 30.

**0.18 — Deposit в LifeWorm**
Сумма депозита и дедлайн должны быть ВИДНЫ во время фокус-сессии. "₽2000 на кону" — мощнейший мотиватор прямо в момент работы. Сейчас это незамеченная связь.

---

## PHASE 13 — Background Processing + Real-time Foundation
*Без этой фазы всё остальное не имеет смысла*

### Цель
Переместить все AI-вызовы в фоновые задачи. Добавить SSE для реального времени. Критические индексы БД.

### Новые файлы

```
backend/app/workers/
  __init__.py
  arq_settings.py          — настройки ARQ (Redis connection, queues)
  tasks/
    ai_tasks.py            — фоновые AI-задачи (plan generation, message processing)
    notification_tasks.py  — отправка push/telegram уведомлений
    energy_tasks.py        — пересчёт energy pattern learning
backend/app/api/v1/
  sse.py                   — SSE endpoint /events/stream
backend/alembic/versions/
  0009_add_indexes.py      — индексы на всех tenant-таблицах
```

### Изменяемые файлы

```
backend/app/main.py                    — lifespan: запуск ARQ worker
backend/app/services/secretary.py      — generatePlan() → enqueue задачу вместо sync
backend/app/api/v1/secretary.py        — POST /secretary/plan → 202 Accepted + job_id
backend/docker-compose.prod.yml        — сервис arq-worker
backend/pyproject.toml                 — добавить arq>=0.25.0
```

---

### Task 13.1: Database indexes migration

**Files:**
- Create: `backend/alembic/versions/0009_add_indexes.py`
- Test: `backend/tests/test_indexes.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_indexes.py
import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_user_id_indexes_exist(db):
    """Every tenant table must have an index on user_id."""
    TENANT_TABLES = [
        "commands", "capture_records", "energy_checkins", "energy_scores",
        "plan_steps", "day_plans", "goals", "tasks", "time_blocks",
        "focus_sessions", "reflections", "push_subscriptions",
    ]
    for table in TENANT_TABLES:
        result = await db.execute(text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename = :t AND indexdef LIKE '%user_id%'
        """), {"t": table})
        count = result.scalar()
        assert count >= 1, f"Missing user_id index on {table}"

@pytest.mark.asyncio
async def test_created_at_indexes_exist(db):
    result = await db.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename = 'commands' AND indexdef LIKE '%created_at%'
    """))
    assert result.scalar() >= 1
```

- [ ] **Step 2: Run — verify FAIL**
```bash
cd backend && pytest tests/test_indexes.py -v
# Expected: FAIL — indexes don't exist yet
```

- [ ] **Step 3: Write migration**

```python
# backend/alembic/versions/0009_add_indexes.py
"""add performance indexes

Revision ID: 0009
Revises: 0008
"""
from alembic import op

_TENANT_TABLES = [
    "commands", "capture_records", "energy_checkins", "energy_scores",
    "plan_steps", "day_plans", "goals", "tasks", "time_blocks",
    "focus_sessions", "reflections", "push_subscriptions",
    "habit_definitions", "habit_entries", "commitment_deposits",
    "commitment_events", "notifications", "user_preferences",
    "life_worm_sessions", "ai_interactions", "weekly_reviews",
    "onboarding_progress",
]

def upgrade() -> None:
    for table in _TENANT_TABLES:
        op.execute(f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_user_id
            ON {table} (user_id)
        """)
        op.execute(f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_user_id_created_at
            ON {table} (user_id, created_at DESC)
        """)
    # Специфичные индексы
    op.execute("CREATE INDEX IF NOT EXISTS ix_day_plans_plan_date ON day_plans (user_id, plan_date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_goals_horizon ON goals (user_id, horizon, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commands_status ON commands (user_id, status, created_at DESC)")

def downgrade() -> None:
    for table in _TENANT_TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_user_id")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_user_id_created_at")
```

- [ ] **Step 4: Run migration and verify PASS**
```bash
alembic upgrade head
pytest tests/test_indexes.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "perf: add user_id + created_at indexes on all tenant tables (migration 0009)"
```

---

### Task 13.2: ARQ worker setup

**Files:**
- Create: `backend/app/workers/arq_settings.py`
- Create: `backend/app/workers/tasks/ai_tasks.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/docker-compose.prod.yml`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_arq_worker.py
import pytest
from app.workers.arq_settings import WorkerSettings

def test_worker_settings_has_redis():
    assert WorkerSettings.redis_settings is not None

def test_worker_settings_has_functions():
    fn_names = [f.__name__ for f in WorkerSettings.functions]
    assert "generate_plan_task" in fn_names
    assert "process_morning_brief_task" in fn_names
```

- [ ] **Step 2: Run — verify FAIL**
```bash
pytest tests/test_arq_worker.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: Install ARQ**

```toml
# backend/pyproject.toml — в [project.dependencies] добавить:
"arq>=0.25.0",
```

- [ ] **Step 4: Create worker settings**

```python
# backend/app/workers/arq_settings.py
from arq.connections import RedisSettings
from app.core.config import settings


async def generate_plan_task(ctx, user_id: str, token: str) -> dict:
    """Background task: generate day plan via Secretary."""
    from app.services.secretary import SecretaryService
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        svc = SecretaryService(db)
        plan = await svc.generate_plan(user_id)
        return {"plan_id": str(plan.id), "status": "done"}


async def process_morning_brief_task(ctx, user_id: str) -> dict:
    """Background task: generate AI morning brief for dashboard."""
    from app.services.ai_client import AIClient
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        client = AIClient(db)
        brief = await client.generate_morning_brief(user_id)
        # Cache in Redis with 6h TTL
        await ctx["redis"].setex(f"brief:{user_id}", 21600, brief)
        return {"status": "done"}


class WorkerSettings:
    functions = [generate_plan_task, process_morning_brief_task]
    redis_settings = RedisSettings.from_dsn(
        __import__("os").getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    max_jobs = 10
    job_timeout = 120
    keep_result = 3600
```

- [ ] **Step 5: Run — verify PASS**
```bash
pytest tests/test_arq_worker.py -v
# Expected: PASS
```

- [ ] **Step 6: Add arq-worker service to docker-compose.prod.yml**

```yaml
# В docker-compose.prod.yml добавить сервис:
  arq-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: ["python", "-m", "arq", "app.workers.arq_settings.WorkerSettings"]
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/exocortex
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      KEYCLOAK_URL: http://keycloak:8080
      KEYCLOAK_REALM: exocortex
      EXOCORTEX_SECRET_KEY: ${EXOCORTEX_SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always
    logging:
      driver: "json-file"
      options: { max-size: "20m", max-file: "5" }
```

- [ ] **Step 7: Commit**
```bash
git add -A && git commit -m "feat: add ARQ background worker with plan generation and morning brief tasks"
```

---

### Task 13.3: Secretary plan generation → async

**Files:**
- Modify: `backend/app/api/v1/secretary.py`
- Create: `backend/tests/test_secretary_async.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_secretary_async.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_generate_plan_returns_202(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/secretary/plan", headers=auth_headers)
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "queued"

@pytest.mark.asyncio
async def test_plan_status_endpoint(client: AsyncClient, auth_headers):
    # Queue a job first
    resp = await client.post("/api/v1/secretary/plan", headers=auth_headers)
    job_id = resp.json()["job_id"]
    # Check status
    resp2 = await client.get(f"/api/v1/secretary/plan/status/{job_id}", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] in ("queued", "in_progress", "done", "failed")
```

- [ ] **Step 2: Run — verify FAIL**
```bash
pytest tests/test_secretary_async.py -v
# Expected: FAIL — still returns 200 synchronously
```

- [ ] **Step 3: Update secretary router**

```python
# backend/app/api/v1/secretary.py — изменить POST /secretary/plan
from arq import create_pool
from arq.connections import RedisSettings
from app.workers.arq_settings import WorkerSettings
import os

@router.post("/secretary/plan", status_code=202)
async def generate_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await create_pool(WorkerSettings.redis_settings)
    job = await redis.enqueue_job(
        "generate_plan_task",
        str(current_user.id),
        _job_id=f"plan:{current_user.id}:{date.today()}",
    )
    return {"job_id": job.job_id, "status": "queued"}


@router.get("/secretary/plan/status/{job_id}")
async def plan_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    redis = await create_pool(WorkerSettings.redis_settings)
    job = await redis.job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    info = await job.info()
    return {
        "job_id": job_id,
        "status": info.status.value if info else "unknown",
        "result": info.result if info and info.success else None,
    }
```

- [ ] **Step 4: Run — verify PASS**
```bash
pytest tests/test_secretary_async.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "feat: plan generation is now async (202 + job_id), status endpoint added"
```

---

### Task 13.4: SSE endpoint for real-time dashboard

**Files:**
- Create: `backend/app/api/v1/sse.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_sse.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_sse.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_sse_endpoint_exists(client: AsyncClient, auth_headers):
    # SSE returns text/event-stream
    async with client.stream("GET", "/api/v1/events/stream", headers=auth_headers) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        # Read first event (heartbeat)
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json
                data = json.loads(line[5:].strip())
                assert data["type"] == "heartbeat"
                break
```

- [ ] **Step 2: Run — verify FAIL**

- [ ] **Step 3: Create SSE router**

```python
# backend/app/api/v1/sse.py
import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/events", tags=["sse"])


async def _event_generator(user_id: str):
    """Yields SSE events for a specific user."""
    import redis.asyncio as aioredis
    from app.core.config import settings

    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"user:{user_id}:events")

    try:
        # Initial heartbeat
        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=25)
            if msg:
                yield f"data: {msg['data'].decode()}\n\n"
            else:
                # Keepalive ping every 25s
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            await asyncio.sleep(0.1)
    finally:
        await pubsub.unsubscribe(f"user:{user_id}:events")
        await r.aclose()


@router.get("/stream")
async def event_stream(current_user: User = Depends(get_current_user)):
    return StreamingResponse(
        _event_generator(str(current_user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

```python
# backend/app/main.py — добавить в router includes:
from app.api.v1.sse import router as sse_router
app.include_router(sse_router, prefix="/api/v1")
```

- [ ] **Step 4: Run — verify PASS**
- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "feat: SSE endpoint /api/v1/events/stream for real-time dashboard updates"
```

---

## PHASE 14 — Task Management UI (Inbox + CRUD + Habits)

### Новые файлы

```
backend/app/api/v1/
  inbox.py              — GET /inbox (все captures с AI-оценкой)
  tasks_crud.py         — POST/GET/PUT/DELETE /tasks
  habits.py             — CRUD привычек + ежедневный трекинг
frontend/app/(app)/
  inbox/page.tsx        — Inbox view
  tasks/page.tsx        — Полный список задач
  habits/page.tsx       — Трекер привычек
frontend/components/
  InboxItem.tsx
  TaskRow.tsx
  HabitTracker.tsx
  QuickWinsQueue.tsx    — Очередь лягушек
```

---

### Task 14.1: Inbox API с AI-сортировкой

**Files:**
- Create: `backend/app/api/v1/inbox.py`
- Create: `backend/tests/test_inbox.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_inbox.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_inbox_returns_sorted_captures(client: AsyncClient, auth_headers, db):
    # Create 3 captures with different urgency
    for raw in ["Срочно: позвонить клиенту", "Когда-нибудь прочитать книгу", "Купить молоко"]:
        await client.post("/api/v1/commands", json={"raw_input": raw}, headers=auth_headers)

    resp = await client.get("/api/v1/inbox", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 3
    # First item should have highest urgency score
    assert items[0]["urgency_score"] >= items[-1]["urgency_score"]

@pytest.mark.asyncio
async def test_inbox_pagination(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/inbox?limit=2&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert len(body["items"]) <= 2
```

- [ ] **Step 2: Run — verify FAIL**

- [ ] **Step 3: Create inbox router**

```python
# backend/app/api/v1/inbox.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from app.models.command import Command
from app.api.deps import get_current_user, get_db

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("")
async def get_inbox(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    total_q = select(func.count()).where(
        Command.user_id == current_user.id,
        Command.status.in_(["pending", "captured"]),
    )
    total = (await db.execute(total_q)).scalar()

    items_q = (
        select(Command)
        .where(
            Command.user_id == current_user.id,
            Command.status.in_(["pending", "captured"]),
        )
        .order_by(Command.urgency_score.desc().nullslast(), Command.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(items_q)).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": str(r.id),
                "raw_input": r.raw_input,
                "status": r.status,
                "urgency_score": r.urgency_score,
                "complexity": r.complexity,
                "estimated_minutes": r.estimated_minutes,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.delete("/{command_id}", status_code=204)
async def dismiss_from_inbox(
    command_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    q = select(Command).where(
        Command.id == command_id,
        Command.user_id == current_user.id,
    )
    cmd = (await db.execute(q)).scalar_one_or_none()
    if not cmd:
        raise HTTPException(404)
    cmd.status = "dismissed"
    await db.commit()
```

- [ ] **Step 4: Run — verify PASS**
- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "feat: GET /inbox with urgency sorting and pagination"
```

---

### Task 14.2: Habits API

**Files:**
- Create: `backend/app/api/v1/habits.py`
- Create: `backend/tests/test_habits.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_habits.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_habit(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/habits", json={
        "title": "Медитация 10 минут",
        "frequency": "daily",
        "target_time": "08:00",
        "estimated_minutes": 10,
    }, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Медитация 10 минут"
    assert "id" in body

@pytest.mark.asyncio
async def test_check_habit(client: AsyncClient, auth_headers):
    # Create
    habit = (await client.post("/api/v1/habits", json={
        "title": "Зарядка", "frequency": "daily"
    }, headers=auth_headers)).json()
    # Check in
    resp = await client.post(f"/api/v1/habits/{habit['id']}/checkin", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["streak"] >= 1

@pytest.mark.asyncio
async def test_habit_streak_increments(client: AsyncClient, auth_headers):
    habit = (await client.post("/api/v1/habits", json={
        "title": "Бег", "frequency": "daily"
    }, headers=auth_headers)).json()
    # First checkin
    r1 = await client.post(f"/api/v1/habits/{habit['id']}/checkin", headers=auth_headers)
    assert r1.json()["streak"] == 1
    # Same day checkin — no double-count
    r2 = await client.post(f"/api/v1/habits/{habit['id']}/checkin", headers=auth_headers)
    assert r2.json()["streak"] == 1
```

- [ ] **Step 2: Run — verify FAIL**

- [ ] **Step 3: Create habits router**

```python
# backend/app/api/v1/habits.py
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from app.models.habit import HabitDefinition, HabitEntry
from app.api.deps import get_current_user, get_db

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(BaseModel):
    title: str
    frequency: str = "daily"   # daily | weekdays | custom
    target_time: str | None = None
    estimated_minutes: int = 10


@router.post("", status_code=201)
async def create_habit(body: HabitCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    habit = HabitDefinition(
        user_id=current_user.id,
        title=body.title,
        frequency=body.frequency,
        target_time=body.target_time,
        estimated_minutes=body.estimated_minutes,
    )
    db.add(habit)
    await db.commit()
    await db.refresh(habit)
    return {"id": str(habit.id), "title": habit.title, "streak": 0}


@router.get("")
async def list_habits(current_user=Depends(get_current_user), db=Depends(get_db)):
    q = select(HabitDefinition).where(
        HabitDefinition.user_id == current_user.id,
        HabitDefinition.is_active == True,
    )
    habits = (await db.execute(q)).scalars().all()
    result = []
    for h in habits:
        streak = await _calculate_streak(str(h.id), db)
        checked_today = await _checked_today(str(h.id), db)
        result.append({
            "id": str(h.id),
            "title": h.title,
            "frequency": h.frequency,
            "streak": streak,
            "checked_today": checked_today,
        })
    return result


@router.post("/{habit_id}/checkin")
async def checkin_habit(habit_id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    q = select(HabitDefinition).where(
        HabitDefinition.id == habit_id,
        HabitDefinition.user_id == current_user.id,
    )
    habit = (await db.execute(q)).scalar_one_or_none()
    if not habit:
        raise HTTPException(404)
    # Idempotent — don't create duplicate entry for today
    today = date.today()
    existing_q = select(HabitEntry).where(
        HabitEntry.habit_id == habit_id,
        func.date(HabitEntry.completed_at) == today,
    )
    if (await db.execute(existing_q)).scalar_one_or_none():
        streak = await _calculate_streak(habit_id, db)
        return {"streak": streak, "already_done": True}

    entry = HabitEntry(habit_id=habit_id, user_id=current_user.id)
    db.add(entry)
    await db.commit()
    streak = await _calculate_streak(habit_id, db)
    return {"streak": streak, "already_done": False}


async def _calculate_streak(habit_id: str, db) -> int:
    entries_q = (
        select(func.date(HabitEntry.completed_at).label("d"))
        .where(HabitEntry.habit_id == habit_id)
        .order_by(func.date(HabitEntry.completed_at).desc())
    )
    rows = (await db.execute(entries_q)).fetchall()
    dates = [r.d for r in rows]
    if not dates:
        return 0
    streak = 0
    check = date.today()
    for d in dates:
        if d == check or d == check - timedelta(days=1):
            streak += 1
            check = d - timedelta(days=1)
        else:
            break
    return streak


async def _checked_today(habit_id: str, db) -> bool:
    q = select(HabitEntry).where(
        HabitEntry.habit_id == habit_id,
        func.date(HabitEntry.completed_at) == date.today(),
    )
    return (await db.execute(q)).scalar_one_or_none() is not None
```

- [ ] **Step 4: Run — verify PASS**
- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "feat: habits API with streak calculation and idempotent daily checkin"
```

---

### Task 14.3: Frontend — Inbox page

**Files:**
- Create: `frontend/app/(app)/inbox/page.tsx`
- Create: `frontend/components/InboxItem.tsx`

```tsx
// frontend/components/InboxItem.tsx
"use client";
import { useState } from "react";

interface InboxItemProps {
  item: {
    id: string;
    raw_input: string;
    urgency_score: number | null;
    estimated_minutes: number | null;
    created_at: string;
  };
  token: string;
  onDismiss: (id: string) => void;
}

const urgencyColor = (score: number | null) => {
  if (!score) return "border-gray-800";
  if (score >= 80) return "border-red-700";
  if (score >= 50) return "border-amber-700";
  return "border-gray-800";
};

export function InboxItem({ item, token, onDismiss }: InboxItemProps) {
  const [loading, setLoading] = useState(false);

  async function dismiss() {
    setLoading(true);
    await fetch(`/api/backend/inbox/${item.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    onDismiss(item.id);
  }

  return (
    <div className={`rounded-xl border p-4 bg-gray-900 ${urgencyColor(item.urgency_score)}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-gray-200 flex-1">{item.raw_input}</p>
        <div className="flex gap-2 flex-shrink-0">
          {item.estimated_minutes && (
            <span className="text-xs text-gray-500">{item.estimated_minutes}m</span>
          )}
          <button
            onClick={dismiss}
            disabled={loading}
            className="text-xs text-gray-600 hover:text-red-400 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-600 mt-1">
        {new Date(item.created_at).toLocaleDateString()}
      </p>
    </div>
  );
}
```

```tsx
// frontend/app/(app)/inbox/page.tsx
import { auth } from "@/auth";
import { api } from "@/lib/api";
import { InboxClientPage } from "./client";

export default async function InboxPage() {
  const session = await auth();
  const token = session!.accessToken;
  const data = await api.inbox.list(token).catch(() => ({ items: [], total: 0 }));
  return <InboxClientPage initialData={data} token={token} />;
}
```

- [ ] **Commit**
```bash
git add -A && git commit -m "feat: inbox page with urgency-sorted captures and dismiss"
```

---

### Task 14.4: Frontend — Habits page

```tsx
// frontend/app/(app)/habits/page.tsx
"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";

interface Habit {
  id: string;
  title: string;
  streak: number;
  checked_today: boolean;
}

export default function HabitsPage() {
  const { data: session } = useSession();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [newTitle, setNewTitle] = useState("");

  async function load() {
    if (!session?.accessToken) return;
    const res = await fetch("/api/backend/habits", {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    });
    setHabits(await res.json());
  }

  useEffect(() => { load(); }, [session]);

  async function checkin(id: string) {
    await fetch(`/api/backend/habits/${id}/checkin`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session!.accessToken}` },
    });
    load();
  }

  async function create() {
    if (!newTitle.trim()) return;
    await fetch("/api/backend/habits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session!.accessToken}`,
      },
      body: JSON.stringify({ title: newTitle }),
    });
    setNewTitle("");
    load();
  }

  return (
    <div className="p-6 max-w-xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold text-white">Habits</h1>

      {/* Add new */}
      <div className="flex gap-2">
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === "Enter" && create()}
          placeholder="New habit..."
          className="flex-1 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 px-3 py-2 text-sm"
        />
        <button onClick={create} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white">
          Add
        </button>
      </div>

      {/* List */}
      {habits.map(h => (
        <div key={h.id} className="flex items-center justify-between rounded-xl bg-gray-900 border border-gray-800 px-5 py-4">
          <div>
            <p className="text-sm font-medium text-gray-200">{h.title}</p>
            <p className="text-xs text-gray-500">🔥 {h.streak} day streak</p>
          </div>
          <button
            onClick={() => checkin(h.id)}
            className={`w-8 h-8 rounded-full border-2 flex items-center justify-center transition-colors ${
              h.checked_today
                ? "border-green-500 bg-green-900 text-green-400"
                : "border-gray-700 hover:border-indigo-500"
            }`}
          >
            {h.checked_today ? "✓" : ""}
          </button>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add -A && git commit -m "feat: habits tracking page with streak and daily checkin"
```

---

## PHASE 15 — Enhanced Dashboard v2

### Новые файлы

```
backend/app/services/morning_brief.py   — AI генерация утреннего брифа
backend/app/api/v1/brief.py             — GET /brief/today
frontend/components/
  MorningBrief.tsx                      — Карточка брифа
  ScheduleTimeline.tsx                  — Временная шкала дня
  GoalsPulse.tsx                        — Прогресс по целям
  CommitmentsAtRisk.tsx                 — Риски и депозиты
  QuickActions.tsx                      — Обновлённые quick actions
frontend/app/(app)/dashboard/
  page.tsx                              — Рефактор: 7 зон
  _components/                          — Серверные компоненты зон
```

---

### Task 15.1: Morning Brief service

**Files:**
- Create: `backend/app/services/morning_brief.py`
- Create: `backend/app/api/v1/brief.py`
- Create: `backend/tests/test_morning_brief.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_morning_brief.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.morning_brief import MorningBriefService

@pytest.mark.asyncio
async def test_brief_contains_required_sections(db, mock_user):
    with patch("app.services.morning_brief.AIClient") as MockAI:
        MockAI.return_value.complete = AsyncMock(return_value=(
            "• Клиент Иванов ждёт ответа 2 дня — КРИТИЧНО\n"
            "• Встреча в 15:00 — повестка не согласована\n"
            "• Цель Q2 отстаёт на 11%"
        ))
        svc = MorningBriefService(db)
        brief = await svc.generate(str(mock_user.id))
        assert len(brief["bullets"]) >= 1
        assert "generated_at" in brief

@pytest.mark.asyncio
async def test_brief_cached_in_redis(db, mock_user, redis_client):
    svc = MorningBriefService(db, redis=redis_client)
    # Prime cache manually
    import json
    await redis_client.setex(
        f"brief:{mock_user.id}",
        21600,
        json.dumps({"bullets": ["test"], "generated_at": "2026-05-26"})
    )
    brief = await svc.get_or_generate(str(mock_user.id))
    assert brief["bullets"] == ["test"]
```

- [ ] **Step 2: Run — verify FAIL**

- [ ] **Step 3: Implement MorningBriefService**

```python
# backend/app/services/morning_brief.py
import json
from datetime import date
from sqlalchemy import select
from app.models.goal import Goal
from app.models.energy import EnergyScore
from app.models.commitment import CommitmentDeposit
from app.services.ai_client import AIClient


class MorningBriefService:
    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis

    async def get_or_generate(self, user_id: str) -> dict:
        if self.redis:
            cached = await self.redis.get(f"brief:{user_id}")
            if cached:
                return json.loads(cached)
        return await self.generate(user_id)

    async def generate(self, user_id: str) -> dict:
        context = await self._build_context(user_id)
        client = AIClient(self.db)
        raw = await client.complete(
            system=(
                "You are an executive assistant giving a morning briefing. "
                "Be concise — 3-5 bullet points maximum. "
                "Prioritize: urgent responses needed, deadlines today, goal risks. "
                "Respond in the user's language."
            ),
            user=f"Morning briefing context:\n{json.dumps(context, ensure_ascii=False)}",
        )
        bullets = [line.lstrip("•- ").strip() for line in raw.strip().split("\n") if line.strip()]
        result = {"bullets": bullets, "generated_at": date.today().isoformat()}
        if self.redis:
            await self.redis.setex(f"brief:{user_id}", 21600, json.dumps(result))
        return result

    async def _build_context(self, user_id: str) -> dict:
        # Active goals behind schedule
        goals_q = select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
        goals = (await self.db.execute(goals_q)).scalars().all()

        # Deposits expiring soon
        deposits_q = select(CommitmentDeposit).where(
            CommitmentDeposit.user_id == user_id,
            CommitmentDeposit.status == "held",
        )
        deposits = (await self.db.execute(deposits_q)).scalars().all()

        # Latest energy
        energy_q = (
            select(EnergyScore)
            .where(EnergyScore.user_id == user_id)
            .order_by(EnergyScore.calculated_at.desc())
            .limit(1)
        )
        energy = (await self.db.execute(energy_q)).scalar_one_or_none()

        return {
            "energy_state": energy.energy_state if energy else "unknown",
            "energy_score": energy.composite_score if energy else None,
            "active_goals_count": len(goals),
            "deposits_expiring": [
                {"amount": d.amount_cents / 100, "due_date": d.due_date.isoformat()}
                for d in deposits
                if d.due_date
            ],
        }
```

- [ ] **Step 4: Run — verify PASS**
- [ ] **Step 5: Commit**
```bash
git add -A && git commit -m "feat: MorningBriefService with Redis caching and AI generation"
```

---

### Task 15.2: Dashboard v2 — 7 zones

**Files:**
- Modify: `frontend/app/(app)/dashboard/page.tsx` — полный рефактор
- Create: `frontend/components/MorningBrief.tsx`
- Create: `frontend/components/GoalsPulse.tsx`
- Create: `frontend/components/CommitmentsAtRisk.tsx`
- Create: `frontend/components/ScheduleTimeline.tsx`

```tsx
// frontend/app/(app)/dashboard/page.tsx
import { auth } from "@/auth";
import { api } from "@/lib/api";
import { EnergyCard } from "@/components/EnergyCard";
import { DailyPlanCard } from "@/components/DailyPlanCard";
import { MorningBrief } from "@/components/MorningBrief";
import { GoalsPulse } from "@/components/GoalsPulse";
import { CommitmentsAtRisk } from "@/components/CommitmentsAtRisk";
import { ScheduleTimeline } from "@/components/ScheduleTimeline";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await auth();
  const token = session!.accessToken;

  const [energy, plan, brief, goals, deposits] = await Promise.allSettled([
    api.energy.score(token),
    api.secretary.todayPlan(token),
    api.brief.today(token),
    api.planning.goals(token, { status: "active", limit: 5 }),
    api.deposits.list(token, { status: "held" }),
  ]).then(r => r.map(x => x.status === "fulfilled" ? x.value : null));

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      {/* Zone 1: Status bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Today</h1>
        <span className="text-sm text-gray-400">
          {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
        </span>
      </div>

      {/* Zone 2: Morning Brief */}
      {brief && <MorningBrief brief={brief} />}

      {/* Zone 3+4: Two-column main area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Inbox Intelligence */}
        <div className="space-y-3">
          {energy ? (
            <EnergyCard energy={energy} />
          ) : (
            <Link href="/energy" className="block rounded-xl border border-dashed border-gray-700 p-5 text-center hover:border-indigo-500 transition-colors">
              <p className="text-gray-400 text-sm">No morning check-in yet</p>
              <p className="text-indigo-400 text-xs mt-1 font-medium">→ Do check-in (30 sec)</p>
            </Link>
          )}
          {plan && <DailyPlanCard plan={plan} token={token} />}
        </div>

        {/* Right: Schedule */}
        <ScheduleTimeline plan={plan} />
      </div>

      {/* Zone 6: Goals Pulse */}
      {goals && goals.length > 0 && <GoalsPulse goals={goals} />}

      {/* Zone 7: Commitments at Risk */}
      {deposits && deposits.length > 0 && <CommitmentsAtRisk deposits={deposits} token={token} />}

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { href: "/focus",   label: "Focus",   icon: "⚡" },
          { href: "/inbox",   label: "Inbox",   icon: "📥" },
          { href: "/habits",  label: "Habits",  icon: "🔁" },
          { href: "/chat/core_advisor", label: "Advisor", icon: "🧠" },
        ].map(({ href, label, icon }) => (
          <Link key={href} href={href}
            className="flex flex-col items-center gap-1 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 p-3 transition-colors">
            <span className="text-xl">{icon}</span>
            <span className="text-xs text-gray-400">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

```tsx
// frontend/components/MorningBrief.tsx
export function MorningBrief({ brief }: { brief: { bullets: string[] } }) {
  return (
    <div className="rounded-xl bg-indigo-950 border border-indigo-800 p-4">
      <p className="text-xs font-semibold text-indigo-400 mb-2 uppercase tracking-wider">
        🧠 AI Morning Brief
      </p>
      <ul className="space-y-1">
        {brief.bullets.map((b, i) => (
          <li key={i} className="text-sm text-gray-300 flex gap-2">
            <span className="text-indigo-500 flex-shrink-0">•</span>
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

```tsx
// frontend/components/GoalsPulse.tsx
import type { PlanningGoal } from "@/lib/types";

export function GoalsPulse({ goals }: { goals: PlanningGoal[] }) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Goals Pulse
      </p>
      <div className="space-y-3">
        {goals.slice(0, 3).map(g => (
          <div key={g.id}>
            <div className="flex justify-between mb-1">
              <span className="text-xs text-gray-300 truncate flex-1 mr-2">{g.title}</span>
              <span className="text-xs text-gray-500 flex-shrink-0">{g.horizon}</span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-800">
              <div
                className="h-1.5 rounded-full bg-indigo-500"
                style={{ width: `${(g.progress_pct ?? 0)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

```tsx
// frontend/components/CommitmentsAtRisk.tsx
import type { CommitmentDeposit } from "@/lib/types";

export function CommitmentsAtRisk({ deposits }: { deposits: CommitmentDeposit[] }) {
  const today = new Date();
  const atRisk = deposits.filter(d => {
    const due = new Date(d.due_date);
    const daysLeft = Math.ceil((due.getTime() - today.getTime()) / 86400000);
    return daysLeft <= 3;
  });

  if (!atRisk.length) return null;

  return (
    <div className="rounded-xl bg-red-950 border border-red-800 p-4">
      <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
        ⚠️ Commitments at Risk
      </p>
      {atRisk.map(d => {
        const due = new Date(d.due_date);
        const daysLeft = Math.ceil((due.getTime() - today.getTime()) / 86400000);
        return (
          <div key={d.id} className="flex justify-between text-sm py-1">
            <span className="text-gray-300">
              {(d.amount_cents / 100).toFixed(0)} {d.currency}
            </span>
            <span className={daysLeft <= 1 ? "text-red-400 font-bold" : "text-amber-400"}>
              {daysLeft <= 0 ? "TODAY" : `${daysLeft}d left`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add -A && git commit -m "feat: dashboard v2 with 7 zones — brief, goals pulse, commitments at risk"
```

---

## PHASE 16 — Telegram Bot v2 (Full Conversational Interface)

### Новые файлы

```
backend/app/services/telegram_bot.py     — Command handlers
backend/app/api/v1/telegram.py           — Webhook (уже есть, расширяем)
backend/tests/test_telegram_bot.py
```

### Команды бота

| Команда / сообщение | Действие |
|---------------------|----------|
| `/start` | Онбординг / приветствие |
| `/checkin` | Запуск energy check-in диалогом |
| `/plan` | Показать план на сегодня |
| `/capture <текст>` | Захватить мысль |
| Голосовое сообщение | Whisper → transcribe → capture |
| `/brief` | AI morning brief |
| `/done <N>` | Отметить шаг N выполненным |
| `/habits` | Список привычек + чекин |
| `/deposit` | Статус депозитов |

---

### Task 16.1: Telegram bot handlers

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_telegram_bot.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.telegram_bot import TelegramBotHandler

@pytest.mark.asyncio
async def test_capture_command(db, mock_user):
    handler = TelegramBotHandler(db)
    with patch.object(handler, "_get_user_by_telegram_id", return_value=mock_user):
        result = await handler.handle_text(
            telegram_id=12345,
            text="/capture Позвонить клиенту завтра"
        )
    assert "captured" in result.lower() or "захвачено" in result.lower()

@pytest.mark.asyncio
async def test_checkin_flow_starts(db, mock_user):
    handler = TelegramBotHandler(db)
    with patch.object(handler, "_get_user_by_telegram_id", return_value=mock_user):
        result = await handler.handle_text(telegram_id=12345, text="/checkin")
    assert "сон" in result.lower() or "sleep" in result.lower()

@pytest.mark.asyncio
async def test_voice_message_transcribed(db, mock_user):
    handler = TelegramBotHandler(db)
    with patch("app.services.telegram_bot.transcribe_voice", return_value="позвонить маме"):
        with patch.object(handler, "_get_user_by_telegram_id", return_value=mock_user):
            result = await handler.handle_voice(telegram_id=12345, file_path="/tmp/voice.ogg")
    assert "позвонить маме" in result or "captured" in result.lower()
```

- [ ] **Step 2: Run — verify FAIL**

- [ ] **Step 3: Implement handler**

```python
# backend/app/services/telegram_bot.py
import httpx
from app.services.whisper import transcribe_voice
from app.services.ai_client import AIClient

CHECKIN_STATE: dict[int, dict] = {}   # In-memory FSM per telegram_id (use Redis in prod)


class TelegramBotHandler:
    def __init__(self, db):
        self.db = db

    async def handle_text(self, telegram_id: int, text: str) -> str:
        user = await self._get_user_by_telegram_id(telegram_id)
        if not user:
            return "Пожалуйста, войдите на сайте и привяжите Telegram."

        # Check-in FSM
        if telegram_id in CHECKIN_STATE:
            return await self._process_checkin_step(telegram_id, user, text)

        cmd = text.strip().split()[0].lower()

        if cmd == "/checkin":
            CHECKIN_STATE[telegram_id] = {"step": "sleep", "values": {}}
            return "Оцени качество сна от 1 до 5\n1 = ужасно, 5 = отлично"

        if cmd == "/capture" or (not cmd.startswith("/")):
            raw = text.lstrip("/capture").strip() if cmd == "/capture" else text
            await self._capture(str(user.id), raw)
            return f"✅ Захвачено: «{raw[:60]}»"

        if cmd == "/plan":
            return await self._get_plan_text(str(user.id))

        if cmd == "/brief":
            from app.services.morning_brief import MorningBriefService
            svc = MorningBriefService(self.db)
            brief = await svc.get_or_generate(str(user.id))
            bullets = "\n".join(f"• {b}" for b in brief["bullets"])
            return f"🧠 Утренний бриф:\n\n{bullets}"

        if cmd == "/habits":
            return await self._get_habits_text(str(user.id))

        return "Команды: /checkin /plan /brief /habits /capture <текст>"

    async def handle_voice(self, telegram_id: int, file_path: str) -> str:
        user = await self._get_user_by_telegram_id(telegram_id)
        if not user:
            return "Не авторизован."
        text = await transcribe_voice(file_path)
        await self._capture(str(user.id), text)
        return f"🎤 Транскрибировано и захвачено:\n«{text[:100]}»"

    async def _process_checkin_step(self, telegram_id: int, user, text: str) -> str:
        state = CHECKIN_STATE[telegram_id]
        try:
            value = int(text.strip())
            if not 1 <= value <= 5:
                raise ValueError
        except ValueError:
            return "Введи число от 1 до 5"

        step = state["step"]
        state["values"][step] = value

        if step == "sleep":
            state["step"] = "mood"
            return "Оцени настроение от 1 до 5"
        if step == "mood":
            state["step"] = "energy"
            return "Оцени уровень энергии от 1 до 5"
        if step == "energy":
            del CHECKIN_STATE[telegram_id]
            vals = state["values"]
            from app.services.energy_service import EnergyService
            svc = EnergyService(self.db)
            score = await svc.checkin(str(user.id), {
                "sleep_quality": vals["sleep"],
                "mood": vals["mood"],
                "energy_level": value,
            })
            emoji = {"sufficient": "🟢", "constrained": "🟡", "critical": "🔴"}.get(score.energy_state, "⚪")
            return (
                f"{emoji} Состояние: {score.energy_state}\n"
                f"Score: {score.composite_score}/100\n\n"
                f"Теперь напиши /plan чтобы получить план дня."
            )

    async def _capture(self, user_id: str, raw: str) -> None:
        from app.models.command import Command
        cmd = Command(user_id=user_id, raw_input=raw, status="pending")
        self.db.add(cmd)
        await self.db.commit()

    async def _get_plan_text(self, user_id: str) -> str:
        from app.models.day_plan import DayPlan, PlanStep
        from sqlalchemy import select
        from datetime import date
        q = (select(DayPlan)
             .where(DayPlan.user_id == user_id, DayPlan.plan_date == date.today())
             .order_by(DayPlan.created_at.desc()).limit(1))
        plan = (await self.db.execute(q)).scalar_one_or_none()
        if not plan:
            return "📋 Плана на сегодня нет. Зайди на сайт и нажми Generate Plan."
        steps = "\n".join(
            f"{i+1}. {s.title} (~{s.estimated_minutes}м)"
            for i, s in enumerate(plan.items[:8])
        )
        return f"📋 План на сегодня:\n\n{steps}"

    async def _get_user_by_telegram_id(self, telegram_id: int):
        from app.models.user_preferences import UserPreferences
        from sqlalchemy import select
        q = select(UserPreferences).where(UserPreferences.telegram_id == str(telegram_id))
        prefs = (await self.db.execute(q)).scalar_one_or_none()
        if not prefs:
            return None
        from app.models.user import User
        return (await self.db.execute(select(User).where(User.id == prefs.user_id))).scalar_one_or_none()

    async def _get_habits_text(self, user_id: str) -> str:
        from app.api.v1.habits import list_habits
        # Simplified — in real impl use service layer
        return "Привычки: /habits_checkin <id> для отметки"
```

```python
# backend/app/services/whisper.py
import httpx
import os

async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice file using OpenAI Whisper API."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # Fallback: return placeholder (Whisper not configured)
        return "[voice message — configure openai_api_key for transcription]"
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": ("audio.ogg", f, "audio/ogg")},
                data={"model": "whisper-1", "language": "ru"},
                timeout=30,
            )
        resp.raise_for_status()
        return resp.json()["text"]
```

- [ ] **Step 4: Update webhook to use handler**

```python
# backend/app/api/v1/telegram.py — обновить webhook
from app.services.telegram_bot import TelegramBotHandler

@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    message = body.get("message", {})
    telegram_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    if not telegram_id:
        return {"ok": True}

    handler = TelegramBotHandler(db)

    if "voice" in message:
        # Download voice file
        file_id = message["voice"]["file_id"]
        file_path = await _download_telegram_file(file_id)
        reply = await handler.handle_voice(telegram_id, file_path)
    else:
        text = message.get("text", "")
        reply = await handler.handle_text(telegram_id, text)

    # Send reply
    await _send_telegram_message(chat_id, reply)
    return {"ok": True}
```

- [ ] **Step 5: Run — verify PASS**
- [ ] **Step 6: Commit**
```bash
git add -A && git commit -m "feat: Telegram bot v2 — full conversational interface, voice capture via Whisper"
```

---

## PHASE 17 — Unified Inbox (Gmail Integration)

### Новые файлы

```
backend/app/integrations/
  gmail/
    oauth.py            — OAuth2 flow
    fetcher.py          — Fetch + parse messages
    sender.py           — Send replies via Gmail API
  message_processor.py  — AI scoring + draft generation
backend/app/models/
  unified_message.py    — Таблица unified_messages
backend/alembic/versions/
  0010_unified_messages.py
backend/app/api/v1/
  messages.py           — GET /messages, POST /messages/{id}/reply
frontend/app/(app)/
  messages/page.tsx     — Unified inbox UI
```

---

### Task 17.1: unified_messages table

```python
# backend/alembic/versions/0010_unified_messages.py
"""unified messages table

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        "unified_messages",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),   # gmail|telegram|whatsapp|linkedin
        sa.Column("external_id", sa.String(500), nullable=False),  # Message ID in source system
        sa.Column("sender_name", sa.String(200)),
        sa.Column("sender_email", sa.String(200)),
        sa.Column("subject", sa.String(500)),
        sa.Column("body_text", sa.Text()),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("requires_reply", sa.Boolean(), default=False),
        sa.Column("urgency_score", sa.Integer()),   # 0-100
        sa.Column("importance_score", sa.Integer()), # 0-100
        sa.Column("ai_summary", sa.Text()),
        sa.Column("ai_draft_1", sa.Text()),   # Quick reply
        sa.Column("ai_draft_2", sa.Text()),   # Balanced reply
        sa.Column("ai_draft_3", sa.Text()),   # Detailed reply
        sa.Column("status", sa.String(50), default="unread"),  # unread|read|replied|snoozed|dismissed
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_unified_messages_user_id", "unified_messages", ["user_id"])
    op.create_index("ix_unified_messages_urgency", "unified_messages", ["user_id", "urgency_score"])
    op.create_index("ix_unified_messages_status", "unified_messages", ["user_id", "status"])
    op.create_unique_constraint(
        "uq_unified_messages_external",
        "unified_messages",
        ["user_id", "channel", "external_id"]
    )

def downgrade() -> None:
    op.drop_table("unified_messages")
```

---

### Task 17.2: Gmail OAuth + fetch

```python
# backend/app/integrations/gmail/oauth.py
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.core.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def create_flow(redirect_uri: str) -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
```

```python
# backend/app/integrations/gmail/fetcher.py
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


async def fetch_unread_messages(credentials: Credentials, max_results: int = 50) -> list[dict]:
    service = build("gmail", "v1", credentials=credentials)
    results = service.users().messages().list(
        userId="me",
        q="is:unread -category:promotions -category:social",
        maxResults=max_results,
    ).execute()

    messages = []
    for msg_ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        snippet = msg.get("snippet", "")

        messages.append({
            "external_id": msg["id"],
            "sender_name": _parse_name(headers.get("From", "")),
            "sender_email": _parse_email(headers.get("From", "")),
            "subject": headers.get("Subject", "(no subject)"),
            "body_text": snippet,
            "received_at": headers.get("Date"),
        })
    return messages


def _parse_name(from_header: str) -> str:
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"')
    return from_header

def _parse_email(from_header: str) -> str:
    if "<" in from_header:
        return from_header.split("<")[1].rstrip(">")
    return from_header
```

```python
# backend/app/integrations/message_processor.py
from app.services.ai_client import AIClient
import json


class MessageProcessor:
    def __init__(self, db):
        self.client = AIClient(db)

    async def score_and_draft(self, message: dict, user_goals: list[str]) -> dict:
        """Score importance and generate 3 reply drafts."""
        prompt = f"""
Message from {message['sender_name']} <{message['sender_email']}>:
Subject: {message['subject']}
Body: {message['body_text'][:500]}

User's active goals: {', '.join(user_goals[:5])}

Respond in JSON:
{{
  "requires_reply": true/false,
  "urgency_score": 0-100,
  "importance_score": 0-100,
  "ai_summary": "one sentence",
  "draft_quick": "1-2 sentence reply",
  "draft_balanced": "paragraph reply",
  "draft_detailed": "full reply with all points"
}}
"""
        raw = await self.client.complete(
            system="You are an AI email assistant. Always respond in valid JSON.",
            user=prompt,
        )
        try:
            return json.loads(raw)
        except Exception:
            return {
                "requires_reply": False,
                "urgency_score": 20,
                "importance_score": 20,
                "ai_summary": message["body_text"][:100],
                "draft_quick": "",
                "draft_balanced": "",
                "draft_detailed": "",
            }
```

- [ ] **Commit**
```bash
git add -A && git commit -m "feat: Gmail integration — OAuth, message fetching, AI scoring and draft generation"
```

---

## PHASE 18 — Robustness v2

### Task 18.1: Circuit breaker for AI calls

```python
# backend/app/services/ai_client.py — добавить circuit breaker
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx


def _ai_retry():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )


class AIClient:
    # ... существующий код ...

    @_ai_retry()
    async def complete(self, system: str, user: str, tier: int = 2) -> str:
        """Complete with automatic retry + exponential backoff."""
        try:
            return await self._complete_with_fallback(system, user, tier)
        except Exception as e:
            # Log to Sentry if configured
            _capture_exception(e)
            raise


def _capture_exception(exc: Exception) -> None:
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except ImportError:
        pass
```

---

### Task 18.2: Sentry integration

```python
# backend/app/main.py — добавить Sentry init
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.core.config import settings

def create_app() -> FastAPI:
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
    # ... rest of app setup
```

```python
# backend/app/core/config.py — добавить поле
class Settings(BaseSettings):
    # ... существующие поля ...
    SENTRY_DSN: str | None = None
```

```yaml
# docker-compose.prod.yml — добавить в api environment:
SENTRY_DSN: ${SENTRY_DSN:-}
```

```
# .env.production.example — добавить:
# Error monitoring (optional but recommended for production)
# Get DSN at sentry.io — free tier available
SENTRY_DSN=
```

---

### Task 18.3: Redis caching для energy score

```python
# backend/app/api/v1/energy.py — добавить кэш
import json
import redis.asyncio as aioredis
from app.core.config import settings

async def _get_redis():
    return aioredis.from_url(settings.REDIS_URL)

@router.get("/energy/score")
async def get_energy_score(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    cache_key = f"energy_score:{current_user.id}"
    r = await _get_redis()

    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    score = await EnergyService(db).get_latest_score(str(current_user.id))
    if score:
        await r.setex(cache_key, 3600, json.dumps(score.to_dict()))  # 1h TTL
    return score
```

---

### Task 18.4: GDPR data export

```python
# backend/app/api/v1/gdpr.py
import json
import zipfile
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text

router = APIRouter(prefix="/gdpr", tags=["gdpr"])

@router.get("/export")
async def export_user_data(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Export all user data as JSON in a ZIP archive."""
    TABLES = [
        "commands", "energy_checkins", "energy_scores", "day_plans",
        "goals", "habit_definitions", "habit_entries", "commitment_deposits",
        "focus_sessions", "reflections",
    ]
    data = {}
    for table in TABLES:
        rows = (await db.execute(
            text(f"SELECT * FROM {table} WHERE user_id = :uid"),
            {"uid": str(current_user.id)},
        )).fetchall()
        data[table] = [dict(r._mapping) for r in rows]

    # Serialize to JSON (handle UUID and datetime)
    def default(o):
        import uuid, datetime
        if isinstance(o, (uuid.UUID,)):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        raise TypeError

    json_bytes = json.dumps(data, indent=2, default=default).encode()

    # Package as ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("exocortex_data_export.json", json_bytes)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=exocortex_export.zip"},
    )


@router.delete("/delete-account", status_code=204)
async def delete_account(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Hard delete all user data (GDPR right to erasure)."""
    TABLES = [
        "push_subscriptions", "notifications", "user_preferences",
        "habit_entries", "habit_definitions", "commitment_events",
        "commitment_deposits", "focus_sessions", "life_worm_sessions",
        "reflections", "weekly_reviews", "ai_interactions", "onboarding_progress",
        "day_plans", "plan_steps", "time_blocks", "tasks", "goals",
        "energy_scores", "energy_checkins", "capture_records", "commands",
    ]
    for table in TABLES:
        await db.execute(
            text(f"DELETE FROM {table} WHERE user_id = :uid"),
            {"uid": str(current_user.id)},
        )
    await db.commit()
```

- [ ] **Commit Phase 18**
```bash
git add -A && git commit -m "feat: robustness v2 — circuit breaker, Sentry, Redis cache, GDPR export/delete"
```

---

## PHASE 19 — Energy Pattern Learning

### Task 19.1: Pattern analysis service

```python
# backend/app/services/energy_patterns.py
from collections import defaultdict
from sqlalchemy import select
from app.models.energy import EnergyCheckin

class EnergyPatternService:
    def __init__(self, db):
        self.db = db

    async def predict_today(self, user_id: str) -> dict | None:
        """Predict today's energy based on historical checkins."""
        from datetime import date
        checkins_q = (
            select(EnergyCheckin)
            .where(EnergyCheckin.user_id == user_id)
            .order_by(EnergyCheckin.created_at.desc())
            .limit(60)
        )
        checkins = (await self.db.execute(checkins_q)).scalars().all()
        if len(checkins) < 10:
            return None  # Not enough data

        today_dow = date.today().weekday()  # 0=Monday
        same_dow = [c for c in checkins if c.created_at.weekday() == today_dow]
        if len(same_dow) < 3:
            return None

        avg_composite = sum(
            (c.sleep_quality + c.mood + c.energy_level) / 15 * 100
            for c in same_dow
        ) / len(same_dow)

        return {
            "predicted_score": round(avg_composite),
            "based_on_samples": len(same_dow),
            "day_of_week": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][today_dow],
            "confidence": "high" if len(same_dow) >= 6 else "medium",
        }
```

```python
# backend/app/api/v1/energy.py — добавить prediction endpoint
@router.get("/energy/prediction")
async def get_energy_prediction(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    svc = EnergyPatternService(db)
    prediction = await svc.predict_today(str(current_user.id))
    if not prediction:
        return {"available": False, "reason": "Not enough data (need 10+ checkins)"}
    return {"available": True, **prediction}
```

Frontend: добавить на страницу Energy Check-In — показывать "На основе 8 предыдущих понедельников, ожидается ~42/100. Подтвердить?" с кнопками быстрого подтверждения.

---

## PHASE 20 — Mobile v2 + PWA

### Task 20.1: Progressive Web App (PWA)

```javascript
// frontend/public/sw.js — Service Worker
const CACHE_NAME = "exocortex-v1";
const OFFLINE_URLS = ["/", "/dashboard", "/energy", "/plan"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(event.request).then(r => r || caches.match("/"))
      )
    );
  }
});
```

```json
// frontend/public/manifest.json
{
  "name": "ExoCortex",
  "short_name": "ExoCortex",
  "description": "Your external cognitive cortex",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#6366f1",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### Task 20.2: Deposit visibility in LifeWorm

```tsx
// mobile/app/(tabs)/worm.tsx — добавить депозит
// В компонент добавить блок:
{activeDeposit && (
  <View style={styles.depositBadge}>
    <Text style={styles.depositText}>
      💰 {activeDeposit.amount} {activeDeposit.currency} on the line
    </Text>
    <Text style={styles.depositDue}>
      Due: {new Date(activeDeposit.due_date).toLocaleDateString()}
    </Text>
  </View>
)}
```

---

## ИТОГОВАЯ КАРТА ИЗМЕНЕНИЙ

### Новые зависимости

```toml
# backend/pyproject.toml добавить:
"arq>=0.25.0",
"tenacity>=8.2.0",
"sentry-sdk[fastapi]>=2.0.0",
"google-api-python-client>=2.0.0",
"google-auth-oauthlib>=1.0.0",
"redis[hiredis]>=5.0.0",
```

```json
// frontend/package.json добавить:
"eventsource": "^2.0.2"
```

### Новые env-переменные

```env
# .env.production.example добавить:
SENTRY_DSN=                              # Опционально, sentry.io
GOOGLE_CLIENT_ID=                        # Для Gmail OAuth
GOOGLE_CLIENT_SECRET=                    # Для Gmail OAuth
OPENAI_API_KEY=                          # Для Whisper transcription (опционально)
```

### Новые API routes (итог)

| Method | Path | Phase |
|--------|------|-------|
| GET | `/api/v1/events/stream` | 13 |
| GET/DELETE | `/api/v1/inbox` | 14 |
| POST/GET | `/api/v1/habits` | 14 |
| POST | `/api/v1/habits/{id}/checkin` | 14 |
| GET | `/api/v1/brief/today` | 15 |
| GET | `/api/v1/energy/prediction` | 19 |
| GET | `/api/v1/messages` | 17 |
| POST | `/api/v1/messages/{id}/reply` | 17 |
| GET | `/api/v1/gdpr/export` | 18 |
| DELETE | `/api/v1/gdpr/delete-account` | 18 |
| GET | `/api/v1/secretary/plan/status/{job_id}` | 13 |

### Новые frontend pages

| Path | Phase |
|------|-------|
| `/inbox` | 14 |
| `/habits` | 14 |
| `/messages` | 17 |
| `/settings/integrations` | 17 |

### Порядок внедрения (жёсткий)

```
Phase 13 (Foundation) → ОБЯЗАТЕЛЬНО ПЕРВОЙ
    └→ Phase 14 (Task Management) — можно параллельно с 15
    └→ Phase 15 (Dashboard v2) — требует 13
    └→ Phase 16 (Telegram) — требует 13
Phase 17 (Gmail) → после 13+14
Phase 18 (Robustness) → можно параллельно с любой
Phase 19 (Energy Patterns) → после 3+ месяцев данных или мок-данных
Phase 20 (PWA+Mobile v2) → последней
```

---

*Plan saved. Ready for execution via subagent-driven-development.*
