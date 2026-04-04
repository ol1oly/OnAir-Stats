@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
set "MODE=%~1"

if /i "%MODE%"=="build" (
    echo [dev] Building frontend...
    cd /d "%ROOT%frontend"
    call npm run build

    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        pause
        exit /b 1
    )

    echo [dev] Build complete.
    cd /d "%ROOT%"

    start "Backend" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
    goto end
)

if /i "%MODE%"=="backend" (
    echo [dev] Starting backend only...
    start "Backend" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
    goto end
)

rem default (dev mode)
echo [dev] Starting backend + frontend...
start "Backend" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate && python -m uvicorn server:app --reload --port 8000"
start "Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

:end