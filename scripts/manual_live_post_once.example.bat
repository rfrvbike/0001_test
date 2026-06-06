@echo off
setlocal

REM Example only. Do not put real keys in a Git-tracked file.
REM Copy this to scripts\manual_live_post_once.local.bat before editing.
REM The .local.bat pattern is ignored by Git.

set X_API_KEY=REPLACE_WITH_API_KEY
set X_API_SECRET=REPLACE_WITH_API_SECRET
set X_ACCESS_TOKEN=REPLACE_WITH_ACCESS_TOKEN
set X_ACCESS_TOKEN_SECRET=REPLACE_WITH_ACCESS_TOKEN_SECRET

if "%X_API_KEY%"=="REPLACE_WITH_API_KEY" (
    echo Refusing to run: copy this file to manual_live_post_once.local.bat and replace placeholders locally.
    exit /b 1
)

set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

set PYTHON_EXE=python
where python >nul 2>&1
if errorlevel 1 set PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=py

"%PYTHON_EXE%" tools\excel_daily_poster\manual_live_post_once.py --queue data\manual_account_posts.csv --confirm I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET

endlocal
