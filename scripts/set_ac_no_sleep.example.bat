@echo off
setlocal

REM Example only. Do not run this Git-tracked file to change production settings.
REM Copy this to scripts\set_ac_no_sleep.local.bat before editing.
REM The .local.bat pattern is ignored by Git.
REM This changes Windows-wide AC-power sleep behavior, not only the X poster task.

set ENABLE_AC_NO_SLEEP_EXAMPLE=NO

if not "%ENABLE_AC_NO_SLEEP_EXAMPLE%"=="YES" (
    echo Refusing to change power settings.
    echo Copy this file to scripts\set_ac_no_sleep.local.bat and set ENABLE_AC_NO_SLEEP_EXAMPLE=YES locally.
    exit /b 1
)

echo This may require Administrator privileges.
echo This changes AC power sleep timeout only. Battery/DC sleep timeout is not changed.

echo.
echo ===== Before =====
powercfg /getactivescheme
powercfg /query

echo.
echo Setting AC standby timeout to never sleep.
powercfg /change standby-timeout-ac 0

echo.
echo ===== After =====
powercfg /getactivescheme
powercfg /query

echo.
echo AC power sleep timeout was changed to 0 minutes. Battery/DC settings were not changed.

endlocal
pause
