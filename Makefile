# Atalhos de desenvolvimento. Requer Docker (infra), Python 3.12 e Node 20.
SHELL := /bin/bash
API := cd api &&
WEB := cd web &&

.PHONY: help infra infra-down setup migrate seed api worker web test lint all-docker

help:
	@echo "make infra      - sobe Postgres+PostGIS, Redis e Mailpit (docker)"
	@echo "make setup      - cria venv, instala dependências (api e web) e copia .env"
	@echo "make migrate    - aplica as migrations"
	@echo "make seed       - cria configurações, usuários de desenvolvimento e dados de demonstração"
	@echo "make api        - API em http://localhost:8000 (docs em /docs)"
	@echo "make worker     - worker + agendador (Celery)"
	@echo "make web        - site em http://localhost:5173"
	@echo "make test       - testes do backend"
	@echo "make lint       - typecheck e lint do frontend"
	@echo "make all-docker - sobe tudo em containers (infra + api + worker + web em http://localhost:3000)"

infra:
	docker compose up -d db redis mailpit

infra-down:
	docker compose down

setup:
	$(API) python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && [ -f .env ] || cp .env.example .env
	$(WEB) npm install && [ -f .env ] || cp .env.example .env

migrate:
	$(API) ./venv/bin/alembic upgrade head

seed:
	$(API) ./venv/bin/python -m app.seed

api:
	$(API) ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	$(API) ./venv/bin/celery -A app.worker.celery_app worker --beat --loglevel=INFO

web:
	$(WEB) npm run dev

test:
	docker compose exec -T db psql -U tur -d tur -tc "SELECT 1 FROM pg_database WHERE datname='tur_test'" | grep -q 1 || docker compose exec -T db psql -U tur -d tur -c "CREATE DATABASE tur_test"
	$(API) ./venv/bin/python -m pytest -q

lint:
	$(WEB) npm run typecheck && npm run lint

all-docker:
	[ -f api/.env ] || cp api/.env.example api/.env
	docker compose --profile app up -d --build
