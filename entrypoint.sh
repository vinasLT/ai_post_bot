#!/bin/bash
set -e

# Container entrypoint waits for Postgres — default to production DB unless overridden.
export ENVIRONMENT="${ENVIRONMENT:-production}"
export DEBUG="${DEBUG:-false}"

echo "⏳ Waiting for DB ($DB_HOST:$DB_PORT)"
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done

echo "📦 Applying migrations (ENVIRONMENT=$ENVIRONMENT)"
python -c "
from app.config import settings
backend = 'sqlite' if settings.use_sqlite_db else 'postgresql'
print(f'Database backend: {backend}')
if settings.use_sqlite_db:
    print('WARNING: migrations target SQLite — set ENVIRONMENT=production for Postgres')
else:
    print(f'PostgreSQL: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}')
"
alembic upgrade head

echo "🚀 Start App"
exec "$@"