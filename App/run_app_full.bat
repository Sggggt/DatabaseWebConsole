@echo off
setlocal ENABLEDELAYEDEXPANSION

rem Ensure we run from the Task9 directory
cd /d "%~dp0"

echo [1/4] Checking Python environment...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python executable not found. Please install Python 3.10+ and try again.
    goto :end
)

echo.
echo [2/4] Installing/updating required packages...
python install_package.py
if errorlevel 1 (
    echo.
    echo Dependency installation failed. See the error details above.
    goto :end
)

echo.
echo [3/4] Running database setup (Tables/Data)...
python setup_nhs_database.py --reset
if errorlevel 1 (
    echo.
    echo Database setup failed. See the error details above.
    goto :end
)

echo.
echo [4/4] Launching NHS Database web application...
echo Press Ctrl+C to stop the server when you're done.
python nhs_database_app.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo Web application exited with code %EXIT_CODE%.

:end
echo.
pause
