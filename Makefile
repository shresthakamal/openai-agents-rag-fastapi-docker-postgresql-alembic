db:
	docker compose up -d db pgadmin

up:
	docker compose up -d

dev:
	uvicorn app:app --reload --app-dir src

start:
	docker compose -f docker-compose.yml up --force-recreate

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

revision:
	alembic revision --autogenerate -m "$(msg)"

revision-empty:
	alembic revision -m "$(msg)"
