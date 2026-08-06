@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_PATH=%PROJECT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_PATH%" (
    echo Error: .venv is missing. Follow the setup steps in README.md first. 1>&2
    exit /b 1
)

cd /d "%PROJECT_DIR%"

"%PYTHON_PATH%" -m uvicorn pskreporter_local.app:app --host 127.0.0.1 --port 8765 --reload
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
