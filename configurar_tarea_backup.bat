@echo off
title Configurar Tarea Programada - Backup OCDI
echo.
echo ==========================================
echo   CONFIGURAR BACKUP AUTOMATICO DIARIO
echo   Sistema OCDI
echo ==========================================
echo.
echo Esta tarea ejecutara el backup todos los dias a las 08:00 AM.
echo La tarea se llamara: OCDI_Backup_Diario
echo.

set APP_DIR=c:\Users\JJBarajas\Downloads\SSD\APLICACION_SDS_OCDI
set SCRIPT=%APP_DIR%\backup_diario.py

:: Eliminar la tarea si ya existe (para actualizarla)
schtasks /delete /tn "OCDI_Backup_Diario" /f >nul 2>&1

:: Crear la tarea programada
schtasks /create ^
  /tn "OCDI_Backup_Diario" ^
  /tr "python \"%SCRIPT%\"" ^
  /sc daily ^
  /st 08:00 ^
  /ru "%USERNAME%" ^
  /f

if %ERRORLEVEL% == 0 (
    echo.
    echo ✅ Tarea programada creada exitosamente.
    echo    Nombre : OCDI_Backup_Diario
    echo    Horario: Todos los dias a las 08:00 AM
    echo    Script : %SCRIPT%
    echo.
    echo Puedes verificarla en: Panel de control ^> Herramientas administrativas
    echo                        ^> Programador de tareas
) else (
    echo.
    echo ERROR al crear la tarea. Intentando con privilegios elevados...
    echo Ejecuta este archivo como Administrador si el error persiste.
)
echo.
pause
