#!/bin/sh
set -e

echo "[entrypoint] Starting Akin Chat API..."

# ---------------------------------------------------------------------------
# Wait for database to be ready (max 30 seconds)
# ---------------------------------------------------------------------------
DB_HOST="${POSTGRES_HOST:-}"
DB_PORT="${POSTGRES_PORT:-5432}"

if [ -n "$DB_HOST" ]; then
    echo "[entrypoint] Waiting for database at ${DB_HOST}:${DB_PORT}..."

    RETRIES=30
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; do
        RETRIES=$((RETRIES - 1))
        if [ "$RETRIES" -le 0 ]; then
            echo "[entrypoint] ERROR: Database not reachable after 30 seconds"
            exit 1
        fi
        echo "[entrypoint] Database not ready, retrying in 1s... (${RETRIES} left)"
        sleep 1
    done

    echo "[entrypoint] Database is ready."
fi

# ---------------------------------------------------------------------------
# Run Alembic migrations
# ---------------------------------------------------------------------------
if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
    echo "[entrypoint] SKIP_MIGRATIONS=true, skipping Alembic migrations."
else
    echo "[entrypoint] Running Alembic migrations..."
    if alembic upgrade head; then
        echo "[entrypoint] Migrations completed successfully."
    else
        echo "[entrypoint] WARNING: Migrations failed."
        if [ "${MIGRATIONS_MUST_SUCCEED:-false}" = "true" ]; then
            echo "[entrypoint] MIGRATIONS_MUST_SUCCEED=true, aborting."
            exit 1
        fi
        echo "[entrypoint] Continuing anyway (set MIGRATIONS_MUST_SUCCEED=true to abort on failure)."
    fi
fi

# ---------------------------------------------------------------------------
# Start the application
# ---------------------------------------------------------------------------
echo "[entrypoint] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --app-dir src \
    "$@"
