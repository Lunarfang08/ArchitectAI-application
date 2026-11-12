from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import engine
from app.main import app


def test_readiness_does_not_need_a_model():
    with TestClient(app) as client:
        response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_runtime_sqlite_enforces_foreign_keys():
    async with engine.connect() as connection:
        assert await connection.scalar(text("PRAGMA foreign_keys")) == 1
