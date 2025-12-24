#!/bin/bash
# Deploy Lotus CRM on VPS (port 16350)
set -e

echo "=== Lotus CRM Deployment ==="

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example – please edit SECRET_KEY and POSTGRES_PASSWORD!"
    exit 1
fi

mkdir -p backups

echo "Building and starting containers..."
docker compose down 2>/dev/null || true
docker compose up -d --build

echo ""
echo "Deployment complete!"
echo "Access: http://$(hostname -I | awk '{print $1}'):16350"
echo "Login: admin / admin"
echo ""
echo "Backups: ./backups/"
echo "Logs: docker compose logs -f web"
