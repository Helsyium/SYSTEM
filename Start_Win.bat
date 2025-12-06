@echo off
TITLE SYSTEM HUB
CD /D "%~dp0"

ECHO ===================================================
ECHO   SYSTEM HUB - LAUNCHER
ECHO ===================================================
ECHO.

:: 1. Python Bul (python veya py)
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PY_CMD=python
) ELSE (
    py --version >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        SET PY_CMD=py
    ) ELSE (
        ECHO [HATA] Python bulunamadi.
        PAUSE
        EXIT /B
    )
)

:: 2. Venv ve Kutuphane Kontrolu
IF NOT EXIST "venv" (
    ECHO [BILGI] Kurulum yapiliyor...
    %PY_CMD% -m venv venv
    
    ECHO [BILGI] PIP Guncelleniyor...
    venv\Scripts\python.exe -m pip install --upgrade pip
    
    ECHO [BILGI] Gereksinimler yukleniyor...
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: 3. Uygulamayi Baslat (Direkt Venv Python ile)
ECHO.
ECHO [BILGI] Uygulama baslatiliyor...
venv\Scripts\python.exe system/main.py

IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [HATA] Bir sorun olustu.
)

ECHO.
ECHO Kapatmak icin bir tusa basin...
PAUSE
