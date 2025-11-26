@echo off
setlocal ENABLEDELAYEDEXPANSION

rem Ensure we run from this project directory
cd /d "%~dp0"

echo [1/3] Checking Python environment...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python executable not found. Please install Python 3.10+ and try again.
    goto :end
)

echo.
echo [2/3] Installing/updating required packages...
python install_package.py
if errorlevel 1 (
    echo.
    echo Dependency installation failed. See the error details above.
    goto :end
)

echo.
echo [3/3] Launching the database web console...
echo Press Ctrl+C to stop the server when you're done.
python app.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo Web application exited with code %EXIT_CODE%.

:end
echo.
pause
