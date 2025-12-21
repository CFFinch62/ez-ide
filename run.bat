@echo off
IF NOT EXIST venv (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate
python main.py
if %errorlevel% neq 0 (
    echo Application exited with error.
    pause
)
