@echo off
cd /d "%~dp0"
title Compilador de OffStream

echo ==============================================================
echo  Compilando OffStream Portable para Windows (.exe)
echo ==============================================================
echo.

python scripts/build_windows_exe.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Hubo un problema durante la compilacion.
    pause
    exit /b 1
)

echo.
echo ==============================================================
echo  [OK] Compilacion finalizada. Revisa la carpeta 'dist/'
echo ==============================================================
echo.
pause
