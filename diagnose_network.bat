@echo off
TITLE AETHER Network Diagnostics
ECHO ============================================
ECHO   AETHER P2P Network Diagnostics
ECHO ============================================
ECHO.

ECHO [1] Checking if port 54000 is listening...
netstat -an | findstr ":54000"
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARNING] Port 54000 is NOT listening!
) ELSE (
    ECHO [OK] Port 54000 is active.
)
ECHO.

ECHO [2] Checking Windows Firewall rules...
netsh advfirewall firewall show rule name="Aether P2P Ports" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARNING] Firewall rule "Aether P2P Ports" NOT found!
) ELSE (
    ECHO [OK] Firewall rule exists.
    netsh advfirewall firewall show rule name="Aether P2P Ports"
)
ECHO.

ECHO [3] Checking network profile...
powershell -Command "Get-NetConnectionProfile | Select-Object Name, NetworkCategory, InterfaceAlias"
ECHO.
ECHO [INFO] If NetworkCategory is 'Public', change it to 'Private':
ECHO   Settings ^> Network ^& Internet ^> Your Network ^> Network Profile ^> Private
ECHO.

ECHO [4] Getting local IP address...
ipconfig | findstr /i "IPv4"
ECHO.

ECHO [5] Testing if port is reachable from outside...
ECHO Run this command on Mac:
ECHO   telnet [WINDOWS_IP] 54000
ECHO If it connects, the port is open. If timeout, something is blocking.
ECHO.

PAUSE
