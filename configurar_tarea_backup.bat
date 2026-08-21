@echo off
title Configurar Tarea Programada - Backup OCDI
echo.
echo ==========================================
echo   CONFIGURAR BACKUP AUTOMATICO
echo   Sistema OCDI
echo ==========================================
echo.
echo Horario: Lunes a Viernes a las 4:00 PM
echo NOTA: Este metodo requiere ejecutarse como Administrador.
echo Si no tienes permisos de admin, usa el boton de backup
echo que aparece directamente en el portal de la plataforma.
echo.

set APP_DIR=c:\Users\JJBarajas\Downloads\SSD\APLICACION_SDS_OCDI
set SCRIPT=%APP_DIR%\backup_diario.py

:: Buscar Python
for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON_EXE=%%P
    goto :found_python
)
echo ERROR: No se encontro Python en el PATH.
pause
exit /b 1
:found_python

:: Eliminar la tarea si ya existe
schtasks /delete /tn "OCDI_Backup_Diario" /f >nul 2>&1

:: Crear tarea para el usuario actual (lunes a viernes, 4PM)
schtasks /create ^
  /tn "OCDI_Backup_Diario" ^
  /tr "\"%PYTHON_EXE%\" \"%SCRIPT%\"" ^
  /sc weekly ^
  /d MON,TUE,WED,THU,FRI ^
  /st 16:00 ^
  /ru "%USERNAME%" ^
  /f

if %ERRORLEVEL% == 0 (
    echo.
    echo Tarea programada creada exitosamente.
    echo    Nombre  : OCDI_Backup_Diario
    echo    Horario : Lunes a Viernes a las 4:00 PM
    echo    Script  : %SCRIPT%
    echo.
    echo Activando "ejecutar en cuanto sea posible" si el PC estaba apagado a las 4PM...
    powershell -NoProfile -Command "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd; Set-ScheduledTask -TaskName 'OCDI_Backup_Diario' -Settings $s | Out-Null"
    echo.
    echo Puedes verificarla en:
    echo   Panel de control ^> Herramientas administrativas ^> Programador de tareas
) else (
    echo.
    echo No se pudo crear la tarea automatica.
    echo Usa el boton "Hacer backup ahora" en el portal de la plataforma.
)
echo.
pause
