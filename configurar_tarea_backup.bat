@echo off
title Configurar Tarea Programada - Backup OCDI
echo.
echo ==========================================
echo   CONFIGURAR BACKUP AUTOMATICO
echo   Sistema OCDI
echo ==========================================
echo.
echo Horario: Lunes a Viernes a las 4:00 PM
echo Si el PC estaba apagado, el backup corre al encender.
echo.

set APP_DIR=c:\Users\JJBarajas\Downloads\SSD\APLICACION_SDS_OCDI
set SCRIPT=%APP_DIR%\backup_diario.py

:: Buscar el ejecutable de Python
for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON_EXE=%%P
    goto :found_python
)
echo ERROR: No se encontro Python en el PATH.
echo Instala Python y marca "Add Python to PATH".
pause
exit /b 1
:found_python

echo Usando Python: %PYTHON_EXE%
echo.

:: Crear la tarea via PowerShell (soporta StartWhenAvailable)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Unregister-ScheduledTask -TaskName 'OCDI_Backup_Diario' -Confirm:$false -ErrorAction SilentlyContinue; ^
$action   = New-ScheduledTaskAction -Execute '%PYTHON_EXE%' -Argument '\"%SCRIPT%\"'; ^
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '16:00'; ^
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew; ^
Register-ScheduledTask -TaskName 'OCDI_Backup_Diario' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null; ^
Write-Host 'OK'"

if %ERRORLEVEL% == 0 (
    echo.
    echo Tarea programada creada exitosamente.
    echo    Nombre   : OCDI_Backup_Diario
    echo    Horario  : Lunes a Viernes a las 4:00 PM
    echo    Recupera : Si el PC estaba apagado, ejecuta al encender
    echo    Script   : %SCRIPT%
    echo.
    echo Puedes verificarla en:
    echo   Panel de control ^> Herramientas administrativas ^> Programador de tareas
) else (
    echo.
    echo ERROR al crear la tarea.
    echo Ejecuta este archivo como Administrador (clic derecho ^> Ejecutar como administrador).
)
echo.
pause
