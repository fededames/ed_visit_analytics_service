PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
ALEMBIC ?= alembic
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
PYTHONPATH ?= .
DB_SERVICE ?= db

.PHONY: install test test-unit test-integration lint format db-up db-reset db-migrate run-local

install:
	$(PIP) install -e ".[dev]"

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST)

test-unit:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/unit -m unit

test-integration:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/integration -m integration

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

db-up:
	docker compose up $(DB_SERVICE) -d

db-reset:
	docker compose down -v
	docker compose up $(DB_SERVICE) -d

db-migrate:
	$(ALEMBIC) upgrade head

run-local:
	$(PYTHON) run_local.py
