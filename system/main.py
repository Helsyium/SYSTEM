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

if __name__ == "__main__":
    main()
