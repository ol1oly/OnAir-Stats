@echo off
setlocal enabledelayedexpansion
set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set ERRORS=0

echo [setup] NHL Radio Overlay - first-time setup
echo.

:: ---------------------------------------------------------------
:: Python check
:: ---------------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://python.org
    set ERRORS=1
    goto :node_check
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK]    Python %PYVER%

:: ---------------------------------------------------------------
:: Create virtual environment if missing
:: ---------------------------------------------------------------
if not exist "%ROOT%\backend\.venv\Scripts\python.exe" (
    echo [....] Creating backend virtual environment...
    python -m venv "%ROOT%\backend\.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        set ERRORS=1
        goto :node_check
    )
    echo [OK]    Virtual environment created.
) else (
    echo [OK]    Virtual environment already exists.
)

:: ---------------------------------------------------------------
:: Install Python dependencies
:: ---------------------------------------------------------------
echo [....] Installing Python dependencies...

"%ROOT%\backend\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip/setuptools/wheel
    set ERRORS=1
)

echo [....] Installing requirements...

"%ROOT%\backend\.venv\Scripts\python.exe" -m pip install --quiet --only-binary=:all: pydantic-core
"%ROOT%\backend\.venv\Scripts\python.exe" -m pip install --quiet -r "%ROOT%\backend\requirements.txt"

if errorlevel 1 (
    echo [ERROR] pip install failed. Check requirements.txt or your network connection.
    set ERRORS=1
) else (
    echo [OK] Python dependencies installed.
)

:: ---------------------------------------------------------------
:: Node check
:: ---------------------------------------------------------------
:node_check
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node 20+ from https://nodejs.org
    set ERRORS=1
    goto :env_check
)
for /f %%v in ('node --version') do set NODEVER=%%v
echo [OK]    Node.js %NODEVER%

:: ---------------------------------------------------------------
:: Install frontend dependencies
:: ---------------------------------------------------------------
echo [....] Installing frontend dependencies...
cd "%ROOT%\frontend"
call npm install --silent
if errorlevel 1 (
    echo [ERROR] npm install failed.
    set ERRORS=1
) else (
    echo [OK]    Frontend dependencies installed.
)
cd "%ROOT%"

:: ---------------------------------------------------------------
:: Build frontend dist if empty or missing
:: ---------------------------------------------------------------
set DIST_EMPTY=1
if exist "%ROOT%\frontend\dist\" (
    for /f %%f in ('dir /b /a-d "%ROOT%\frontend\dist\" 2^>nul') do set DIST_EMPTY=0
)
if !DIST_EMPTY!==1 (
    echo [....] Building frontend dist/...
    cd "%ROOT%\frontend"
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        set ERRORS=1
    ) else (
        echo [OK]    Frontend dist/ built.
    )
    cd "%ROOT%"
) else (
    echo [OK]    Frontend dist/ already built.
)

:: ---------------------------------------------------------------
:: .env setup
:: ---------------------------------------------------------------
:env_check
if not exist "%ROOT%\.env" (
    if exist "%ROOT%\.env.example" (
        copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
        echo [OK]    Created .env from .env.example.
    ) else (
        echo [WARN]  No .env or .env.example found. Create .env manually.
        set ERRORS=1
        goto :done
    )
) else (
    echo [OK]    .env already exists.
)

:: Check DEEPGRAM_API_KEY is not empty
set DGKEY=
for /f "tokens=1,* delims==" %%a in ('findstr /i "^DEEPGRAM_API_KEY=" "%ROOT%\.env"') do set DGKEY=%%b
if "!DGKEY!"=="" (
    echo [WARN]  DEEPGRAM_API_KEY is not set in .env -- edit .env before running.
    set ERRORS=1
) else (
    echo [OK]    DEEPGRAM_API_KEY is set.
)

:: ---------------------------------------------------------------
:: Done
:: ---------------------------------------------------------------
:done
echo.
if !ERRORS!==0 (
    echo [setup] All done. Run dev.bat to start both servers.
) else (
    echo [setup] Setup finished with warnings. Fix the issues above, then run dev.bat.
)
echo.
pause
