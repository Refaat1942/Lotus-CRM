#!/bin/bash
# Daily PostgreSQL backup script for Lotus CRM
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="lotus_crm_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-lotus}" "${POSTGRES_DB:-lotus_crm}" | gzip > "${BACKUP_DIR}/${FILENAME}"
echo "[$(date)] Backup saved: ${BACKUP_DIR}/${FILENAME}"

find "$BACKUP_DIR" -name "lotus_crm_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Cleaned backups older than ${RETENTION_DAYS} days"
