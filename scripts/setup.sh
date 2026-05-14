#!/bin/bash
# First-time setup script
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Copying .env.example to .env (if not exists)"
[ -f .env ] || cp .env.example .env

echo "==> Starting Docker services (Postgres + Elasticsearch)"
docker compose up -d db elasticsearch

echo "==> Waiting for Postgres to be ready..."
until docker compose exec -T db pg_isready -U decode -d decode_beijing; do
  sleep 2
done

echo "==> Running schema migration"
docker compose exec -T db psql -U decode -d decode_beijing \
  -f /dev/stdin < backend/alembic/versions/001_initial_schema.sql

echo "==> Setting up Python virtual environment"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "==> Setup complete. Next steps:"
echo "    1. Start the API:        cd backend && uvicorn app.main:app --reload"
echo "    2. Run the scraper:      cd backend && scrapy crawl xinhua"
echo "    3. Manual ingest:        python scripts/ingest_manual.py --file doc.txt --title '...' --date 2023-12-11 --type economic_work_conference"
echo "    4. API docs:             http://localhost:8000/docs"
