@echo off
setlocal

set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

if not exist logs mkdir logs

set PYTHON_EXE=python
where python >nul 2>&1
if errorlevel 1 set PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=py

"%PYTHON_EXE%" tools\excel_daily_poster\daily_post.py --queue data\manual_account_posts.csv --dry-run >> logs\excel_daily_poster.log 2>&1

timeout /t 1800 /nobreak

endlocal
