@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv_dating_gui\Scripts\python.exe" (
    echo [ERROR] .venv_dating_gui was not found.
    echo Please run the setup steps in dating_assistant\README.md first.
    pause
    exit /b 1
)

echo Starting dating_assistant GUI...
echo.
echo If the browser does not open automatically, open:
echo http://localhost:8501
echo.

".venv_dating_gui\Scripts\python.exe" -m streamlit run dating_assistant\gui_streamlit_app.py

echo.
echo dating_assistant GUI has stopped.
pause
