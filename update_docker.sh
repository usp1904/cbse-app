#!/bin/bash
# Script to pull latest code from Git and force-rebuild the Docker containers

set -e

# Change to the script's directory to ensure relative paths work
cd "$(dirname "$0")"

echo "=== [1/4] Pulling latest code from Git ==="
git pull

echo ""
echo "=== [2/4] Stopping existing Docker containers ==="
docker compose down --remove-orphans

echo ""
echo "=== [3/4] Rebuilding Docker image without cache ==="
docker compose build --no-cache app

echo ""
echo "=== [4/4] Starting Docker containers (force-recreate) ==="
docker compose up -d --force-recreate

echo ""
echo "=== Setup verification ==="
docker compose ps

echo ""
echo "=== Update complete! CBSE App is running with the latest Git code ==="
