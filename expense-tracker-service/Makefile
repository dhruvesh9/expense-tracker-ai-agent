# Run `make help` to list commands. Uses the project's .venv directly, so you
# don't need to activate it first.
BIN := .venv/bin
DB  := data/expense_tracker.db

.PHONY: help setup start start-debug migrate migration seed seed-generate seed-load reset shell test lint format check

help:  ## Show this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

setup:  ## Create .venv and install requirements
	python3 -m venv .venv && $(BIN)/pip install -r requirements.txt

start:  ## Run the server on port 8001 (auto-reload)
	$(BIN)/uvicorn app.main:app --reload --port 8001

start-debug:  ## Same, with DEBUG logging
	LOG_LEVEL=DEBUG $(BIN)/uvicorn app.main:app --reload --port 8001

migrate:  ## Apply database migrations (creates the DB if missing)
	$(BIN)/alembic upgrade head

migration:  ## Generate a migration: make migration m="add notes column"
	$(BIN)/alembic revision --autogenerate -m "$(m)"

seed:  ## Load dummy data (20-30 users, 10-500 expenses each)
	sqlite3 $(DB) < scripts/seed.sql

seed-generate:  ## New random dataset: make seed-generate [ARGS="--seed 7"]
	$(BIN)/python scripts/generate_seed.py $(ARGS)

seed-load:  ## LOAD TEST: 25k users, ~1.9M expenses (~5k daily actives). Replaces data. make seed-load ARGS="--users 20000 --days 90 --dau 4000"
	$(BIN)/python scripts/generate_load_data.py --wipe $(ARGS)

reset:  ## DELETE the dev DB, then migrate and seed it
	rm -f $(DB)
	$(MAKE) migrate
	$(MAKE) seed

shell:  ## Open the dev DB in sqlite3
	sqlite3 -header -column $(DB)

test:  ## Run the test suite
	$(BIN)/pytest

lint:  ## Lint and check formatting
	$(BIN)/ruff check . && $(BIN)/ruff format --check .

format:  ## Auto-fix lint issues and format code
	$(BIN)/ruff check --fix . && $(BIN)/ruff format .

check: lint test  ## Lint, then test
