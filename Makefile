.PHONY: install lint format test check storage-check
install:
	uv sync
	uv run pre-commit install
lint:
	uv run ruff check .
	uv run ruff format --check .
format:
	uv run ruff check --fix .
	uv run ruff format .
test:
	uv run pytest
check: lint test
storage-check:
	STORAGE_BACKEND=r2 uv run --env-file .env python -m bike_or_bust.check_storage
