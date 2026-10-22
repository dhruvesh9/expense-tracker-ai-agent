#!/bin/sh
# Start command for hosting: migrate, seed demo data if empty, then run the server.
set -e
alembic upgrade head
PYTHONPATH=. python scripts/seed_if_empty.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}"
