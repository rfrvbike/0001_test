@echo off
setlocal

REM Example only. Do not run this Git-tracked file to change production settings.
REM Copy this to scripts\restore_ac_sleep_30min.local.bat before editing.
REM The .local.bat pattern is ignored by Git.
REM This changes Windows-wide AC-power sleep behavior, not only the X poster task.

set RESTORE_AC_SLEEP_30MIN_EXAMPLE=NO

if not "%RESTORE_AC_SLEEP_30MIN_EXAMPLE%"=="YES" (
    echo Refusing to change power settings.
    echo Copy this file to scripts\restore_ac_sleep_30min.local.bat and set RESTORE_AC_SLEEP_30MIN_EXAMPLE=YES locally.
    exit /b 1
)

echo This may require Administrator privileges.
echo This changes AC power sleep timeout only. Battery/DC sleep timeout is not changed.

echo.
echo ===== Before =====
powercfg /getactivescheme
powercfg /query

echo.
echo Restoring AC standby timeout to 30 minutes.
powercfg /change standby-timeout-ac 30

echo.
echo ===== After =====
powercfg /getactivescheme
powercfg /query

echo.
echo AC power sleep timeout was changed to 30 minutes. Battery/DC settings were not changed.

endlocal
pause
