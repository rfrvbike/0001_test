@echo off
setlocal

set PROJECT_DIR=%~dp0..
set TASK_NAME=X Excel Daily Poster Legacy Manual Account
set RUN_BAT=%PROJECT_DIR%\scripts\run_excel_daily_post.bat

schtasks /Create /TN "%TASK_NAME%" /SC DAILY /ST 09:00 /TR "\"%RUN_BAT%\"" /F

endlocal
pause
