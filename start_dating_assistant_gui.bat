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
echo Checking for stale dating_assistant Streamlit processes...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_stale_dating_streamlit.ps1"
if errorlevel 1 (
    echo [WARN] Could not complete stale Streamlit cleanup. Continuing with import preflight.
)
echo.
echo Running GUI import preflight...
".venv_dating_gui\Scripts\python.exe" tools\check_dating_gui_imports.py
if errorlevel 1 (
    echo.
    echo [ERROR] GUI import preflight failed. Streamlit was not started.
    echo Please check the missing import shown above.
    pause
    exit /b 1
)
echo.
echo If the browser does not open automatically, open:
echo http://localhost:8501
echo.

".venv_dating_gui\Scripts\python.exe" -m streamlit run dating_assistant\gui_streamlit_app.py

echo.
echo dating_assistant GUI has stopped.
pause
