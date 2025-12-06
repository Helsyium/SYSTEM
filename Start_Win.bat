@echo off
TITLE SYSTEM HUB
CLS

ECHO ===================================================
ECHO   SYSTEM HUB - Antigravity Inc.
ECHO   Platform: Windows
ECHO ===================================================
ECHO.

:: 1. Proje Dizinine Git
CD /D "%~dp0"

:: 2. Sanal Ortam (venv) Kontrolü
IF NOT EXIST "venv" (
    ECHO [BILGI] Ilk kurulum yapiliyor (Sanal ortam olusturuluyor)...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [HATA] Sanal ortam olusturulamadi. Python yuklu mu?
        PAUSE
        EXIT /B
    )
    ECHO [BILGI] Bagimliliklar yukleniyor...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

:: 3. Başlat
ECHO [BILGI] SYSTEM arayüzü baslatiliyor...
python system/main.py

PAUSE
