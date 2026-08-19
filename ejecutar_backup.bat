@echo off
title Backup OCDI
cd /d "%~dp0"
echo.
echo ==========================================
echo   BACKUP DIARIO - Sistema OCDI
echo ==========================================
echo.
python backup_diario.py
if %ERRORLEVEL% == 0 (
    echo.
    echo Backup completado correctamente.
) else (
    echo.
    echo HUBO UN ERROR en el backup.
    echo Revisa G:\Mi unidad\OCDI_Backup\backup_log.txt
)
echo.
pause
