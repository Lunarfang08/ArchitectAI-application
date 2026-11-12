.PHONY: setup migrate dev-backend dev-frontend test lint docker-up docker-down docker-logs

setup:
	UV_CACHE_DIR=.uv-cache uv sync --project backend --extra dev
	cd backend && UV_CACHE_DIR=../.uv-cache uv run alembic upgrade head
	cd frontend && npm install

migrate:
	cd backend && UV_CACHE_DIR=../.uv-cache uv run alembic upgrade head

dev-backend:
	cd backend && UV_CACHE_DIR=../.uv-cache uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && UV_CACHE_DIR=../.uv-cache uv run pytest
	cd frontend && npm test -- --run

lint:
	cd backend && UV_CACHE_DIR=../.uv-cache uv run ruff check .
	cd frontend && npm run lint

docker-up:
	docker compose up --build -d --wait

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f --tail=100

