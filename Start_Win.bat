ECHO ===================================================
ECHO   SYSTEM HUB - LAUNCHER
ECHO ===================================================
ECHO.

:: WINDOWS ENCODING FIX (Emoji ve Unicode Hatalarini Onler)
SET PYTHONIOENCODING=utf-8
CHCP 65001 >nul

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
)

:: 3. Kutuphaneleri Kontrol Et (OTOMATIK DUZELTME ILE)
ECHO [BILGI] Kutuphaneler kontrol ediliyor...
venv\Scripts\python.exe -m pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    ECHO [UYARI] Standart kurulum basarisiz. Ozel cozum uygulaniyor...
    ECHO [BILGI] AETHER modulu icin ozel kurulum yapiliyor...
    
    venv\Scripts\python.exe -m pip install av==13.0.0
    venv\Scripts\python.exe -m pip install aiortc --no-deps
    venv\Scripts\python.exe -m pip install aioice google-crc32c pyee pylibsrtp ifaddr dnspython opencv-python pyopenssl
    
    ECHO [BILGI] Ozel kurulum tamamlandi.
)

:: 4. Uygulamayi Baslat (Direkt Venv Python ile)
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
