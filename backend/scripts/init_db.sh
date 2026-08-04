#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

DB_NAME="open_hoops"
DB_USER="postgres"

echo "==> Checking Postgres is running..."
if ! pg_isready -U "$DB_USER" > /dev/null 2>&1; then
  echo "ERROR: Postgres is not running. Start it with: brew services start postgresql@16"
  exit 1
fi

echo "==> Creating database '$DB_NAME' (if not exists)..."
createdb -U "$DB_USER" "$DB_NAME" 2>/dev/null || echo "    Database already exists."

echo "==> Generating initial Alembic migration..."
alembic revision --autogenerate -m "initial schema"

echo "==> Running migrations..."
alembic upgrade head

echo "==> Done. Database '$DB_NAME' is ready."
