#!/bin/sh
# Start server — auto-detects environment and chooses the right backend
# Usage: ./start.sh [app|server|mesh]

MODE=${1:-${MODE:-server}}
cd "$(dirname "$0")"

# Auto-install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing FastAPI dependencies..."
    pip3 install -r requirements.txt 2>/dev/null || \
        python3 -m pip install -r requirements.txt 2>/dev/null || \
        echo "WARNING: Could not install dependencies. Install manually: pip install -r requirements.txt"
fi

if [ "$MODE" = "app" ] || [ "$MODE" = "legacy" ]; then
    echo "Starting legacy CBSEHandler on port ${PORT:-9090}..."
    exec python3 server.py
elif [ "$MODE" = "mesh" ]; then
    echo "Starting Mesh Load Balancer on port ${LB_PORT:-9090}..."
    if [ -f mesh_lb.py ]; then
        exec python3 mesh_lb.py
    else
        exec python3 _archive/mesh_lb.py
    fi
else
    echo "Starting FastAPI server on 0.0.0.0:${PORT:-9090} with ${UVICORN_WORKERS:-4} workers..."
    echo "Database: ${DATABASE_URL:-sqlite:///cbse_content.db}"
    exec python3 -m uvicorn server:app \
        --host 0.0.0.0 \
        --port "${PORT:-9090}" \
        --workers "${UVICORN_WORKERS:-4}" \
        --proxy-headers \
        --forwarded-allow-ips='*' \
        --log-level info
fi
