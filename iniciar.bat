@echo off
title OCDI - Sistema de Gestion Disciplinaria SDS
echo.
echo  ============================================
echo   OCDI - Secretaria Distrital de Salud
echo   Sistema de Gestion Disciplinaria
echo  ============================================
echo.

echo  Liberando puerto 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a /T >nul 2>&1
    echo  Proceso %%a detenido.
)
timeout /t 2 /nobreak >nul

echo  Iniciando servidor...
echo.
echo  En ESTE equipo abra:
echo     http://localhost:8000
echo.
echo  Para los DEMAS equipos de la red (recomendado, no cambia aunque cambie la IP):
echo     http://%COMPUTERNAME%:8000
echo.
echo  Alternativa por IP (puede cambiar si TIC modifica la red):
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -ExpandProperty IPv4Address).IPAddress | Where-Object { $_ -notlike '169.254.*' }"`) do echo     http://%%i:8000
echo.
echo  Para detener el servidor presione Ctrl+C
echo.

cd /d "%~dp0"
:: Sin --reload: en Windows --reload obliga a uvicorn a usar select(), que se
:: cae con "WinError 10055" cuando hay muchas conexiones. --reload es solo
:: para desarrollo (recarga al editar codigo); en la oficina no se necesita.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
