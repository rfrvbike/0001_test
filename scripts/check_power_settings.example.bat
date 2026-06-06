@echo off
setlocal

REM Read-only helper. This file only displays Windows power settings.
REM It does not change sleep, hibernate, wake timer, or Task Scheduler settings.
REM Optional local copy:
REM   scripts\check_power_settings.local.bat
REM The .local.bat pattern is ignored by Git.

echo ===== Active power plan =====
powercfg /getactivescheme

echo.
echo ===== Full power settings query =====
echo Look for AC/DC sleep settings and wake timer settings in the output below.
powercfg /query

echo.
echo ===== Current wake timers =====
powercfg /waketimers

echo.
echo This was a read-only check. No Windows power settings were changed.

endlocal
pause
