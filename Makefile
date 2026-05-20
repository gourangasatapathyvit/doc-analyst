.PHONY: dev dev-stop dev-local sync test lint format clean

dev:              ## Start full stack via Docker
	docker compose up -d

dev-stop:         ## Stop all containers
	docker compose down

dev-local:        ## Start without Docker (for debugging)
	@echo "Starting API on :8080..."
	cd apps/api && uv run uvicorn app.main:app --reload --port 8080 &
	@echo "Starting Web on :3000..."
	cd apps/web && pnpm dev &
	@echo "All services started. API: http://localhost:8080, Web: http://localhost:3000"

sync:             ## Install all dependencies
	uv sync
	cd apps/web && pnpm install

test:             ## Run all tests
	uv run pytest apps/api packages/

lint:             ## Lint everything
	uv run ruff check apps/api packages/
	cd apps/web && pnpm lint

format:           ## Format everything
	uv run ruff format apps/api packages/

clean:            ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf apps/api/uploads apps/api/lancedb_data
