@echo off
echo ================================
echo    EZ IDE Setup (Windows)
echo ================================
echo.

REM Check Python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is required but not found.
    echo Please install Python 3.8 or higher from python.org
    echo Ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Error creating virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created.

echo.
echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Upgrading pip...
python -m pip install --upgrade pip -q

echo.
echo Installing dependencies...
padding install PyQt6>=6.5.0 -q
if %errorlevel% neq 0 (
    echo Error installing dependencies.
    pause
    exit /b 1
)
echo Dependencies installed.

echo.
echo ================================
echo    Setup Complete!
echo ================================
echo.
echo To run EZ IDE:
echo   run.bat
echo.
pause
