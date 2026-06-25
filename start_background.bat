@echo off
cd /d "%~dp0"

:: Default to server mode if not specified
set MODE=%1
if "%MODE%"=="" set MODE=server

echo Starting CBSE App in %MODE% mode...

if "%MODE%"=="mesh" (
    :: Run mesh load balancer (runs on port 9090, workers on 9091+)
    python _archive/mesh_lb.py > mesh_lb_windows.log 2>&1
) else (
    :: Run FastAPI directly on port 9090
    python -m uvicorn server:app --host 0.0.0.0 --port 9090 --workers 4 > server_windows.log 2>&1
)
