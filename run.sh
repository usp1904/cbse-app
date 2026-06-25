#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Class X Education Platform ==="
echo ""

# Step 1: Seed database if needed
if [ ! -f cbse_content.db ] || [ "$1" == "--reseed" ]; then
    echo "[1/3] Seeding database with content..."
    python3 seed_content.py
    echo "      Seeding additional subjects..."
    python3 seed_missing_topics.py
    echo ""
fi

# Step 2: Start workers
MODE="${1:-app}"

case "$MODE" in
    app)
        echo "[2/3] Starting web server..."
        echo ""
        python3 server.py
        ;;
    mesh)
        if [ -f mesh_lb.py ]; then
            python3 mesh_lb.py
        else
            python3 _archive/mesh_lb.py
        fi
        ;;
    mcp)
        echo "[2/3] Starting MCP server (stdio)..."
        echo ""
        python3 mcp_server.py
        ;;
    seed)
        echo "[2/3] Already seeded. Exiting."
        exit 0
        ;;
    *)
        echo "Usage: $0 [app|mesh|mcp|seed|--reseed]"
        echo "  app       — Start web server (default)"
        echo "  mesh      — Start mesh load balancer with multiple workers"
        echo "  mcp       — Start MCP server (stdio mode for AI integration)"
        echo "  seed      — Only seed/re-seed database"
        echo "  --reseed  — Force re-seed before starting"
        exit 1
        ;;
esac
