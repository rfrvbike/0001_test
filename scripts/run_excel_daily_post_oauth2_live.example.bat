@echo off
setlocal

REM Example only. Do not run this Git-tracked file as production automation.
REM Copy this to scripts\run_excel_daily_post_oauth2_live.local.bat before editing.
REM The .local.bat pattern is ignored by Git.
REM Required local files:
REM - data\manual_account_posts.csv
REM - data\oauth2_tokens.local.json
REM Required Windows environment variables:
REM - X_OAUTH2_CLIENT_ID
REM - X_OAUTH2_CLIENT_SECRET
REM - X_OAUTH2_REDIRECT_URI

set RUN_OAUTH2_LIVE_EXAMPLE=NO
set RANDOM_DELAY_MINUTES_MAX=120
set SIMILAR_RECENT_POST_CHECK_ENABLED=YES
set SIMILAR_RECENT_POST_DAYS=30
set SIMILAR_RECENT_POST_THRESHOLD=0.85

if not "%RUN_OAUTH2_LIVE_EXAMPLE%"=="YES" (
    echo Refusing to run: copy this file to run_excel_daily_post_oauth2_live.local.bat and set RUN_OAUTH2_LIVE_EXAMPLE=YES locally.
    exit /b 1
)

set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

if not exist logs mkdir logs
set LOG_FILE=logs\excel_daily_poster_oauth2_live.log

echo ===== OAuth2 daily poster started at %DATE% %TIME% ===== >> "%LOG_FILE%"
echo Close Excel before this runner touches data\manual_account_posts.csv. >> "%LOG_FILE%"

if "%X_OAUTH2_CLIENT_ID%"=="" (
    echo Refusing to run: X_OAUTH2_CLIENT_ID is not set. >> "%LOG_FILE%"
    exit /b 1
)

if "%X_OAUTH2_CLIENT_SECRET%"=="" (
    echo Refusing to run: X_OAUTH2_CLIENT_SECRET is not set. >> "%LOG_FILE%"
    exit /b 1
)

if "%X_OAUTH2_REDIRECT_URI%"=="" (
    echo Refusing to run: X_OAUTH2_REDIRECT_URI is not set. >> "%LOG_FILE%"
    exit /b 1
)

if not exist data\manual_account_posts.csv (
    echo Refusing to run: data\manual_account_posts.csv was not found. >> "%LOG_FILE%"
    exit /b 1
)

if not exist data\oauth2_tokens.local.json (
    echo Refusing to run: data\oauth2_tokens.local.json was not found. >> "%LOG_FILE%"
    exit /b 1
)

for /f %%D in ('powershell -NoProfile -Command "$max=[int]$env:RANDOM_DELAY_MINUTES_MAX; Get-Random -Minimum 0 -Maximum ($max + 1)"') do set RANDOM_DELAY_MINUTES=%%D
set /a RANDOM_DELAY_SECONDS=%RANDOM_DELAY_MINUTES%*60
echo Random delay: %RANDOM_DELAY_MINUTES% minutes >> "%LOG_FILE%"

if %RANDOM_DELAY_SECONDS% GTR 0 (
    timeout /t %RANDOM_DELAY_SECONDS% /nobreak >> "%LOG_FILE%" 2>&1
)

set PYTHON_EXE=python
where python >nul 2>&1
if errorlevel 1 set PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=py

"%PYTHON_EXE%" tools\excel_daily_poster\manual_live_post_once.py --queue data\manual_account_posts.csv --use-oauth2 --confirm I_UNDERSTAND_THIS_POSTS_ONE_REAL_X_TWEET >> "%LOG_FILE%" 2>&1

timeout /t 1800 /nobreak

endlocal
