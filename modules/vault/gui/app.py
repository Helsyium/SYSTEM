import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..core.crypto_manager import CryptoManager
from ..core.file_utils import FileManager
from ..utils.config import APP_NAME
from system.core.config import THEME

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("600x450")
        self.resizable(False, False)

        # Değişkenler
        self.crypto_manager = None
        self.file_manager = None
        self.selected_folder = ctk.StringVar(value="Klasör seçilmedi")
        self.status_text = ctk.StringVar(value="Hazır")
        self.is_processing = False

        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Ekranlar
        self.login_frame = LoginFrame(self, self.on_login_success)
        self.main_frame = MainFrame(self)

        # Başlangıçta Login ekranı
        self.show_login()

    def show_login(self):
        self.main_frame.grid_forget()
        self.login_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def show_main(self):
        self.login_frame.grid_forget()
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def on_login_success(self, password):
        # CryptoManager başlat
        try:
            self.crypto_manager = CryptoManager(password)
            self.file_manager = FileManager(self.crypto_manager)
            self.show_main()
        except Exception as e:
            messagebox.showerror("Hata", f"Başlatma hatası: {e}")

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, login_callback):
        super().__init__(master)
        self.login_callback = login_callback
        
        self.grid_columnconfigure(0, weight=1)
        
        # Başlık
        self.label_title = ctk.CTkLabel(self, text="Hoş Geldiniz", font=("Roboto", 24, "bold"))
        self.label_title.grid(row=0, column=0, pady=(40, 10))
        
        self.label_subtitle = ctk.CTkLabel(self, text="Güvenli Klasör Kilitleyici", font=("Roboto", 14))
        self.label_subtitle.grid(row=1, column=0, pady=(0, 30))


        # Şifre Alanı
        self.entry_password = ctk.CTkEntry(self, placeholder_text="Ana Şifre", show="*", width=250)
        self.entry_password.grid(row=2, column=0, pady=(10, 5))
        
        # Şifre Tekrar Alanı
        self.entry_password_confirm = ctk.CTkEntry(self, placeholder_text="Ana Şifre (Tekrar)", show="*", width=250)
        self.entry_password_confirm.grid(row=3, column=0, pady=(5, 10))
        
        # Giriş Butonu
        self.btn_login = ctk.CTkButton(self, text="Giriş Yap / Anahtar Oluştur", command=self.login_action, width=250)
        self.btn_login.grid(row=4, column=0, pady=20)
        
        self.label_info = ctk.CTkLabel(self, text="Not: Bu şifre dosyalarınızı şifrelemek için kullanılacaktır.\nUnutursanız verileriniz kurtarılamaz!", 
                                       text_color="gray", font=("Arial", 10))
        self.label_info.grid(row=5, column=0, pady=10)

    def login_action(self):
        pwd = self.entry_password.get()
        pwd_confirm = self.entry_password_confirm.get()
        
        if len(pwd) < 4:
            messagebox.showwarning("Uyarı", "Şifre en az 4 karakter olmalıdır.")
            return

        if pwd != pwd_confirm:
            messagebox.showerror("Hata", "Şifreler uyuşmuyor!")
            self.entry_password.delete(0, "end")
            self.entry_password_confirm.delete(0, "end")
            return
            
        self.login_callback(pwd)

class MainFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master: App = master
        
        self.grid_columnconfigure(0, weight=1)
        
        # Başlık ve Klasör Seçim Alanı
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        self.lbl_head = ctk.CTkLabel(self.frame_top, text="Klasör İşlemleri", font=("Roboto", 20, "bold"), text_color=THEME["colors"]["text_primary"])
        self.lbl_head.pack(anchor="w")

        # Klasör Seçim Çerçevesi (Modernize)
        self.frame_select = ctk.CTkFrame(self, fg_color=THEME["colors"]["bg_card"])
        self.frame_select.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_select.grid_columnconfigure(0, weight=1)

        # Label'i textvariable yerine statik text ile başlatıyoruz
        self.lbl_folder = ctk.CTkLabel(self.frame_select, text=self.master.selected_folder.get(), wraplength=450, 
                                       font=("Roboto", 13), text_color=THEME["colors"]["text_secondary"])
        self.lbl_folder.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        self.btn_browse = ctk.CTkButton(self.frame_select, text="KLASÖR SEÇ", command=self.browse_folder, width=120,
                                        fg_color=THEME["colors"]["accent"], text_color="black")
        self.btn_browse.grid(row=0, column=1, padx=15, pady=15)

        # İşlem Butonları (Büyük ve Modern)
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.grid(row=2, column=0, pady=30, padx=20, sticky="ew")
        self.frame_actions.grid_columnconfigure((0,1), weight=1) # Eşit genişlik

        self.btn_encrypt = ctk.CTkButton(self.frame_actions, text="🔒 ŞİFRELE (KİLİTLE)", command=lambda: self.start_process('encrypt'), 
                                         fg_color=THEME["colors"]["danger"], hover_color="#b71c1c", 
                                         height=50, font=("Roboto", 16, "bold"))
        self.btn_encrypt.grid(row=0, column=0, padx=10, sticky="ew")

        self.btn_decrypt = ctk.CTkButton(self.frame_actions, text="🔓 ŞİFRE ÇÖZ (AÇ)", command=lambda: self.start_process('decrypt'), 
                                         fg_color=THEME["colors"]["success"], hover_color="#00c853", 
                                         height=50, font=("Roboto", 16, "bold"))
        self.btn_decrypt.grid(row=0, column=1, padx=10, sticky="ew")

        # Durum ve Progress (Daha belirgin)
        self.frame_status = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_status.grid(row=3, column=0, pady=10, sticky="ew", padx=20)
        
        self.lbl_status = ctk.CTkLabel(self.frame_status, textvariable=self.master.status_text, text="Hazır",
                                       text_color=THEME["colors"]["accent"], font=("Roboto", 14))
        self.lbl_status.pack(pady=(10, 5))

        self.progressbar = ctk.CTkProgressBar(self.frame_status, width=400, progress_color=THEME["colors"]["accent"])
        self.progressbar.pack(pady=10, fill="x")
        self.progressbar.set(0)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.master.selected_folder.set(folder)
            # Manuel güncelleme (Bug fix)
            self.lbl_folder.configure(text=folder)

    def start_process(self, mode):
        folder = self.master.selected_folder.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Hata", "Lütfen geçerli bir klasör seçin.")
            return

        if self.master.is_processing:
            return

        if mode == 'encrypt':
            confirmation = messagebox.askyesno("Onay", "Seçilen klasör şifrelenecek. Orijinal dosyalar silinecek. Emin misiniz?")
        else:
            confirmation = messagebox.askyesno("Onay", "Seçilen klasörün şifresi çözülecek. Emin misiniz?")
        
        if not confirmation:
            return

        self.master.is_processing = True
        self.btn_encrypt.configure(state="disabled")
        self.btn_decrypt.configure(state="disabled")
        self.progressbar.start()
        
        # İşlemi thread içinde yap (UI donmasın)
        thread = threading.Thread(target=self.run_process_thread, args=(folder, mode))
        thread.start()

    def run_process_thread(self, folder, mode):
        try:
            self.master.status_text.set(f"İşleniyor: {os.path.basename(folder)}...")
            
            def progress_callback(filename):
                # UI güncelleme (Thread safe değil, ama ctk değişkenleri genelde sorun çıkarmaz, yine de dikkat)
                # Basit callback
                pass

            self.master.file_manager.process_folder(folder, mode, callback=progress_callback)
            
            self.master.status_text.set("İşlem Başarıyla Tamamlandı!")
            self.master.after(0, lambda: messagebox.showinfo("Başarılı", "İşlem tamamlandı."))
        except Exception as e:
            error_msg = str(e)
            self.master.status_text.set("Hata oluştu!")
            self.master.after(0, lambda: messagebox.showerror("Hata", f"İşlem sırasında hata: {error_msg}"))
        finally:
            self.master.is_processing = False
            self.master.after(0, self.reset_ui)

    def reset_ui(self):
        self.btn_encrypt.configure(state="normal")
        self.btn_decrypt.configure(state="normal")
        self.progressbar.stop()
        self.progressbar.set(0)
