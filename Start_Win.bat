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

:: 2. Python Komutunu Belirle (python vs py)
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PYTHON_CMD=python
) ELSE (
    py --version >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        SET PYTHON_CMD=py
    ) ELSE (
        ECHO [HATA] Python bulunamadi!
        ECHO Lutfen Python 3.10+ yukleyin.
        PAUSE
        EXIT /B
    )
)

ECHO [BILGI] Kullanilan Python: %PYTHON_CMD%

:: 3. Sanal Ortam (venv) Kontrolu
IF NOT EXIST "venv" (
    ECHO [BILGI] Ilk kurulum yapiliyor (Sanal ortam olusturuluyor)...
    %PYTHON_CMD% -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [HATA] Sanal ortam olusturulamadi.
        PAUSE
        EXIT /B
    )
    
    ECHO [BILGI] Bagimliliklar yukleniyor...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [HATA] Kutuphaneler yuklenemedi.
        PAUSE
        EXIT /B
    )
) ELSE (
    call venv\Scripts\activate.bat
)

:: 4. Baslat
CLS
ECHO BASLATILIYOR...
python system/main.py

IF %ERRORLEVEL% NEQ 0 (
    ECHO [HATA] Uygulama kapandi. ErrorLevel: %ERRORLEVEL%
)

ECHO.
PAUSE
