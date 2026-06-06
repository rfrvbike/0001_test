@echo off
setlocal

REM Example only. Do not run this Git-tracked file as production automation.
REM Copy this to scripts\register_excel_daily_post_oauth2_live_task.local.bat before editing.
REM The .local.bat pattern is ignored by Git.

set REGISTER_OAUTH2_LIVE_TASK_EXAMPLE=NO

if not "%REGISTER_OAUTH2_LIVE_TASK_EXAMPLE%"=="YES" (
    echo Refusing to register: copy this file to register_excel_daily_post_oauth2_live_task.local.bat and set REGISTER_OAUTH2_LIVE_TASK_EXAMPLE=YES locally.
    exit /b 1
)

set PROJECT_DIR=%~dp0..
set TASK_NAME=X OAuth2 Daily Poster
set RUN_BAT=%PROJECT_DIR%\scripts\run_excel_daily_post_oauth2_live.local.bat

if not exist "%RUN_BAT%" (
    echo Refusing to register: %RUN_BAT% was not found.
    exit /b 1
)

schtasks /Create /TN "%TASK_NAME%" /SC DAILY /ST 21:30 /TR "\"%RUN_BAT%\"" /F

echo Registered task "%TASK_NAME%" for 21:30 daily.
echo Random 0-120 minute posting delay is handled by the local run bat.
echo Open Task Scheduler and review wake-from-sleep settings before relying on automation.

endlocal
pause
