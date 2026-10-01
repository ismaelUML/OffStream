@echo off
setlocal enabledelayedexpansion
title OffStream Desktop Launcher

:: Nos posicionamos en la carpeta donde reside este script para evitar rutas relativas rotas
cd /d "%~dp0"

:: 1. Detectar ejecutable de Python
set "PYTHON_EXE="
set "PYTHONW_EXE="

:: Intentar primero con pythonw en PATH (para no dejar ventanas de consola negras abiertas)
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHONW_EXE=pythonw"
)

:: Verificar python en PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
)

:: Si no está en PATH, buscar en rutas estándar de instalación de usuario en Windows
if "%PYTHON_EXE%"=="" (
    for %%V in (312 311 310 313) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
        )
    )
)

:: Si aún no se encuentra Python, guiar amistosamente al usuario
if "%PYTHON_EXE%"=="" (
    echo.
    echo  =============================================================
    echo   [!] No se encontro Python instalado en el sistema.
    echo  =============================================================
    echo.
    echo   OffStream requiere Python 3.10 o superior para funcionar.
    echo.
    echo   1. Descarga el instalador oficial desde:
    echo      https://www.python.org/downloads/
    echo.
    echo   2. IMPORTANTE: Durante la instalacion, marca la casilla
    echo      "Add python.exe to PATH" antes de hacer clic en Instalar.
    echo.
    echo  =============================================================
    echo.
    pause
    exit /b 1
)

:: 2. Verificar dependencias mínimas (ej. PySide6 para la interfaz gráfica)
"%PYTHON_EXE%" -c "import PySide6, fastapi, yt_dlp" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo  =============================================================
    echo   Preparando dependencias necesarias para OffStream...
    echo  =============================================================
    echo.
    echo   Instalando paquetes desde requirements.txt...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo  [ERROR] Fallo la instalacion de dependencias.
        echo  Verifica tu conexion a Internet e intenta nuevamente.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] Dependencias instaladas correctamente.
    echo.
)

:: 3. Lanzar OffStream Desktop GUI
if not "%PYTHONW_EXE%"=="" (
    start "" "%PYTHONW_EXE%" main.py --gui
) else (
    start "" "%PYTHON_EXE%" main.py --gui
)

exit /b 0
