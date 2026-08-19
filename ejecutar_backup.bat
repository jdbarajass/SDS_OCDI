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
    echo Revisa el archivo backup_log.txt en la carpeta de Google Drive:
    echo G:\Mi unidad\5) DOCUMENTOS PARA CONSEGUIR TRABAJO\Simo\Soportes_SDS\BACKUP_APP_OCDI\Backup_Automatico_OCDI
)
echo.
pause
