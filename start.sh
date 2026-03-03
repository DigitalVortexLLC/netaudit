#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "No .env file found — creating one from .env.example"
    cp .env.example .env
    echo "Please review .env and update passwords/secrets before running in production."
fi

# Build and start all services
echo "Building and starting NetAudit..."
docker compose up --build -d

echo ""
echo "NetAudit is starting up. Services:"
echo "  Frontend:  http://localhost:${FRONTEND_PORT:-3000}"
echo "  Backend:   http://localhost:8000 (API)"
echo ""
echo "View logs with:  docker compose logs -f"
echo "Stop with:       docker compose down"
