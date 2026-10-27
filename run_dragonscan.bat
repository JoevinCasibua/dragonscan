@echo off
title DRAGONSCAN v5.2.0 - 60 GHz FMCW Radar + Logitech C270 Optical Station
cd /d "%~dp0"

echo ========================================================
echo   DRAGONSCAN v5.2.0 - 7-INCH STATION CONTROLLER
echo   60 GHz FMCW RADAR + LOGITECH C270 HD OPTICAL SYSTEM
echo ========================================================
echo.

:: 1. Check for user AppData Python 3.14 installation
set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if exist "%PY_EXE%" (
    echo Starting DragonScan with Python 3.14...
    "%PY_EXE%" main.py
    if %ERRORLEVEL% NEQ 0 pause
    goto end
)

:: 2. Check for standard Windows Python launcher (py.exe)
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting DragonScan Desktop Station with py launcher...
    py -3 main.py
    if %ERRORLEVEL% NEQ 0 pause
    goto end
)

:: 3. Check for system python in PATH
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting DragonScan Desktop Station with system Python...
    python main.py
    if %ERRORLEVEL% NEQ 0 pause
    goto end
)

:: 4. Search other common Local Programs Python paths
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        echo Starting DragonScan with found Python in %%D...
        "%%D\python.exe" main.py
        if %ERRORLEVEL% NEQ 0 pause
        goto end
    )
)

echo [ERROR] Python was not found in PATH or standard installation directories.
echo Please install Python 3.10+ from python.org or add it to PATH.
pause

:end
