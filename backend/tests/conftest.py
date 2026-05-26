import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import TokenClaims, get_current_user
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rls import get_tenant_db
from app.main import app

# Shared test identity — reused across all pipeline tests
TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

TEST_USER = TokenClaims(
    sub=str(TEST_USER_ID),
    user_id=TEST_USER_ID,
    tenant_id=TEST_TENANT_ID,
    email="test@exocortex.test",
    roles=["user"],
)

# Separate test database to avoid polluting dev data
_TEST_DB_URL = settings.DATABASE_URL.replace("/exocortex", "/exocortex_test")

_test_engine = create_async_engine(_TEST_DB_URL, echo=False, poolclass=None)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_test_schema() -> None:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with _TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    async def _override_db():
        yield db

    async def _override_tenant_db():
        yield db

    async def _override_auth():
        return TEST_USER

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_tenant_db] = _override_tenant_db
    app.dependency_overrides[get_current_user] = _override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
