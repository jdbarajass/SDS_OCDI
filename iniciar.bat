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
echo  Una vez iniciado, abra su navegador en:
echo.
echo     http://localhost:8000
echo.
echo  Para otros equipos en la red, use la IP de este PC.
echo  Para detener el servidor presione Ctrl+C
echo.

cd /d "%~dp0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
