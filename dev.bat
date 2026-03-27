@echo off
setlocal

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set BUILD=%1

if "%BUILD%"=="build" (
    echo [dev] Building frontend...
    cd "%ROOT%\frontend"
    call npm run build
    echo [dev] Build complete.
    cd "%ROOT%"
)

echo [dev] Starting backend (port 8000) and frontend dev server (port 5173)...
echo [dev] Close this window or press Ctrl+C to stop both.

start "Backend" cmd /k "cd /d "%ROOT%\backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
start "Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm run dev"

echo [dev] Both servers started in separate windows.
