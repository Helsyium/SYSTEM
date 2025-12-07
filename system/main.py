import os
import sys
import customtkinter as ctk

# Add project root to sys.path to allow absolute imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from system.gui.dashboard import SystemDashboard
from system.core.config import THEME

def main():
    # Global System Settings
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue") # Base theme, overridden by our custom colors
    
    # Launch Dashboard
    app = SystemDashboard()
    app.mainloop()

def configure_firewall():
    """Confingure Windows Firewall to allow Aether P2P traffic."""
    if sys.platform != 'win32':
        return

    try:
        import subprocess
        # 0. AUTO-FIX: Switch Network Profile to Private (Silent)
        # This solves the "Public Network blocks everything" issue
        subprocess.run(
            ["powershell", "-Command", 
             "Set-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -NetworkCategory Private -ErrorAction SilentlyContinue"], 
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        # Also try for Ethernet just in case
        subprocess.run(
            ["powershell", "-Command", 
             "Set-NetConnectionProfile -InterfaceAlias 'Ethernet' -NetworkCategory Private -ErrorAction SilentlyContinue"], 
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        # 1. Allow Port Range (TCP/UDP 54000-54010)
        # We suppress output to keep console clean, errors are printed
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule", 
             "name=Aether P2P Ports", "dir=in", "action=allow", 
             "protocol=TCP", "localport=54000-54010"], 
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule", 
             "name=Aether P2P Ports", "dir=in", "action=allow", 
             "protocol=UDP", "localport=54000-54010"], 
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        # 2. Allow Application Executable (The Smart Fix)
        # This bypasses Public/Private restrictions for this specific app
        app_path = sys.executable
        # If running from venv python, allow it. If frozen exe, allow it.
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule", 
             "name=Aether P2P App", "dir=in", "action=allow", 
             "program=" + app_path, "enable=yes"], 
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        # 3. Allow Python for Development (Optional but helpful)
        if "python" in app_path.lower():
             subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule", 
                 "name=Python Interpreter", "dir=in", "action=allow", 
                 "program=" + app_path, "enable=yes"], 
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

        print("[SYSTEM] Windows Network & Firewall configured successfully.")
    except Exception as e:
        print(f"[SYSTEM] Firewall configuration warning: {e}")

if __name__ == "__main__":
    configure_firewall()
    main()
