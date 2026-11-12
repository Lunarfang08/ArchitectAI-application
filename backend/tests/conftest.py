from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_knowledge_base
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import get_db_session
from app.main import app
from app.services.knowledge import KnowledgeBase


@pytest_asyncio.fixture(autouse=True)
async def isolated_database(tmp_path: Path, monkeypatch: MonkeyPatch) -> AsyncIterator[None]:
    database_path = str(tmp_path) + "/architect_ai_test.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    monkeypatch.setattr(get_settings(), "generated_projects_dir", tmp_path / "generated")
    knowledge = KnowledgeBase(tmp_path / "knowledge", chunk_size=300, chunk_overlap=50)
    app.dependency_overrides[get_knowledge_base] = lambda: knowledge
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_knowledge_base, None)
    await test_engine.dispose()

