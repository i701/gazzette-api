# List available recipes
default:
    @just --list

# Start the dev stack (api with reload, worker, postgres, redis)
dev *args:
    docker compose up --build {{args}}

# Lint with ruff
lint:
    uv run ruff check .

# Lint and apply safe autofixes
lint-fix:
    uv run ruff check --fix .

# Format code with ruff
fmt:
    uv run ruff format .

# Check formatting without changing files
fmt-check:
    uv run ruff format --check .

# Run tests
test *args:
    uv run pytest {{args}}

# Format, autofix lint issues, then run tests
fix: fmt lint-fix test

# Everything CI should run (no file changes)
check: fmt-check lint test
