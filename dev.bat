@echo off
setlocal

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set MODE=%1

if "%MODE%"=="build" (
    echo [dev] Building frontend...
    cd "%ROOT%\frontend"
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        pause
        exit /b 1
    )
    echo [dev] Build complete.
    cd "%ROOT%"
    echo [dev] Starting backend only (port 8000)...
    echo [dev] Open http://localhost:8000 in OBS or your browser.
    echo [dev] Close this window or press Ctrl+C to stop.
    start "Backend" cmd /k "cd /d "%ROOT%\backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
    echo [dev] Backend started in a separate window.
) else (
    echo [dev] Starting backend (port 8000) + Vite dev server (port 5173)...
    echo [dev] Use http://localhost:5173 in your browser for hot-reload.
    echo [dev] Run "dev.bat build" to serve everything from port 8000 instead.
    echo [dev] Close this window or press Ctrl+C to stop both.
    start "Backend" cmd /k "cd /d "%ROOT%\backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
    start "Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm run dev"
    echo [dev] Both servers started in separate windows.
)
