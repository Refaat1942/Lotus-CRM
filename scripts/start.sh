#!/bin/sh
set -e

export SKIP_STARTUP_MIGRATIONS=1

echo "[lotus-crm] Running database init/migrations..."
python scripts/init_db.py

echo "[lotus-crm] Starting web server on port 16350..."
exec gunicorn \
  --bind 0.0.0.0:16350 \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --preload \
  run:app
