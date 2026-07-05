#!/bin/sh
export SKIP_STARTUP_MIGRATIONS=1

echo "[lotus-crm] Running database init/migrations..."
if python scripts/init_db.py; then
  echo "[lotus-crm] Database init OK"
else
  echo "[lotus-crm] WARNING: database init failed — starting web server anyway"
fi

echo "[lotus-crm] Starting web server on port 16350..."
exec gunicorn \
  --bind 0.0.0.0:16350 \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  run:app
