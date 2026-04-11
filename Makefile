.PHONY: dev build test lint install uninstall package

dev:
	npx concurrently \
		"cd frontend && npm run dev" \
		"uv run uvicorn src.weles.api.main:app --reload --port 8000"

build:
	cd frontend && npm run build

test:
	uv run pytest

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src/

install:
	@echo "Implemented in #32"

uninstall:
	@echo "Implemented in #32"

package:
	@echo "Implemented in #32"
