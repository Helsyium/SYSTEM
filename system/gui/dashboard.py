import customtkinter as ctk
from PIL import Image
import os
import sys

from ..core.config import THEME, APP_NAME, MODULES_DIR

# Try Import TkinterDnD (DISABLED FOR STABILITY ON MAC)
try:
    # from tkinterdnd2 import TkinterDnD, DND_FILES
    # DND_AVAILABLE = True
    raise ImportError("DnD Disabled for Stability")
except ImportError:
    # print("TkinterDnD module not found. Drag & Drop disabled.")
    DND_AVAILABLE = False
    # Dummy class
    class TkinterDnD:
        class DnDWrapper: pass

try:
    from modules.vault.gui.app import App as VaultApp
except ImportError as e:
    print(f"Vault modülü yüklenemedi: {e}")
    VaultApp = None

try:
    from modules.shatter.gui.app import ShatterApp
except ImportError as e:
    print(f"Shatter modülü yüklenemedi: {e}")
    ShatterApp = None

# Inherit from DnDWrapper removed for stability
class SystemDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize DnD if available
        if DND_AVAILABLE:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception as e:
                print(f"UYARI: Drag & Drop kutuphanesi yuklenemedi (Runtime Error): {e}")
                globals()['DND_AVAILABLE'] = False

        self.title(APP_NAME)
        self.geometry("1100x700")
        
        # Theme Setup
        self.configure(fg_color=THEME["colors"]["bg_main"])
        
        # Layout: Sidebar (Left) + Content (Right)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_sidebar()
        self.create_main_area()
        
        # State
        self.current_module_app = None

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=THEME["colors"]["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # Logo / Header
        self.logo_label = ctk.CTkLabel(self.sidebar, text="SYSTEM", font=("Roboto", 32, "bold"), text_color=THEME["colors"]["accent"])
        self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 10), sticky="w")
        
        self.version_label = ctk.CTkLabel(self.sidebar, text="v1.0 BETA", font=("Roboto", 12), text_color=THEME["colors"]["text_secondary"])
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 40), sticky="w")
        
        # Navigation Buttons
        self.btn_dashboard = self.create_nav_button("Dashboard", "home", row=2, command=self.show_dashboard)
        self.btn_settings = self.create_nav_button("Settings", "settings", row=3, command=self.show_settings)
        
        # Bottom Status
        self.status_label = ctk.CTkLabel(self.sidebar, text="Sys-Check: OK", font=("Roboto", 12), text_color=THEME["colors"]["success"])
        self.status_label.grid(row=5, column=0, padx=20, pady=20, sticky="w")

    def create_nav_button(self, text, icon_name, row, command):
        btn = ctk.CTkButton(self.sidebar, text=text, command=command,
                            fg_color="transparent", text_color=THEME["colors"]["text_primary"],
                            hover_color=THEME["colors"]["bg_card_hover"],
                            anchor="w", height=40, font=("Roboto", 14))
        btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        return btn

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        # Grid Layout for Cards
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        
        self.show_dashboard()

    def show_dashboard(self):
        # Clear frame
        self.clear_main_frame()
        self.handle_module_close()
        
        # Header
        head = ctk.CTkLabel(self.main_frame, text="Active Modules", font=("Roboto", 24, "bold"), text_color=THEME["colors"]["text_primary"])
        head.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 30))
        
        # Vault Module Card
        self.create_module_card("VAULT", "Secure File Encryption", "LOCKED", 1, 0, self.launch_vault)
        
        # Shatter Module Card
        self.create_module_card("SHATTER", "Military Grade File Shredder", "READY", 1, 1, self.launch_shatter)

    def create_module_card(self, title, subtitle, status, row, col, command):
        card = ctk.CTkFrame(self.main_frame, fg_color=THEME["colors"]["bg_card"], corner_radius=15, border_width=1, border_color=THEME["colors"]["border"])
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Title
        c_title = ctk.CTkLabel(card, text=title, font=("Roboto", 20, "bold"), text_color=THEME["colors"]["accent"])
        c_title.pack(padx=20, pady=(20, 5), anchor="w")
        
        # Subtitle
        c_sub = ctk.CTkLabel(card, text=subtitle, font=("Roboto", 12), text_color=THEME["colors"]["text_secondary"])
        c_sub.pack(padx=20, pady=(0, 20), anchor="w")
        
        # Launch Button
        btn = ctk.CTkButton(card, text="LAUNCH", command=command,
                            fg_color=THEME["colors"]["accent"], text_color=THEME["colors"]["accent_text"],
                            hover_color=THEME["colors"]["accent_hover"],
                            corner_radius=20)
        btn.pack(padx=20, pady=20, fill="x", side="bottom")
        
    def launch_shatter(self):
        if not ShatterApp:
            print("Shatter modülü bulunamadı.")
            return
            
        self.withdraw()
        
        def on_close():
            self.current_module_app.destroy()
            self.current_module_app = None
            self.deiconify()
            self.show_dashboard()
            
        self.current_module_app = ShatterApp()
        self.current_module_app.protocol("WM_DELETE_WINDOW", on_close)
        
        # Toplevel için mainloop çağrılmaz, ana döngüye dahil olur.
        # Pencereyi öne getir
        self.current_module_app.lift()
        self.current_module_app.focus_force()
        # self.current_module_app.mainloop()  <-- REMOVED

    def launch_vault(self):
        if not VaultApp:
            print("Vault modülü yok.")
            return

        # Hide Dashboard Content
        self.clear_main_frame()
        
        self.withdraw() # Main windowu gizle
        
        # Callback to return to dashboard
        def on_close():
            self.current_module_app.destroy()
            self.current_module_app = None
            self.deiconify() # Geri göster
            self.show_dashboard()

        self.current_module_app = VaultApp()
        self.current_module_app.protocol("WM_DELETE_WINDOW", on_close)
        self.current_module_app.mainloop()

        # Not: mainloop burada bloklar. 
        # Eğer dashboard da bir mainloop içindeyse, ikinci mainloop sorun olabilir mi?
        # Evet, nested mainloop tehlikeli.
        # Toplevel olarak açmak daha iyidir.
        
    def show_settings(self):
        self.clear_main_frame()
        lbl = ctk.CTkLabel(self.main_frame, text="Settings - Coming Soon", font=("Roboto", 20))
        lbl.pack(pady=50)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
    def handle_module_close(self):
        # Reset module state if needed
        pass
