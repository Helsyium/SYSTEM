import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..core.crypto_manager import CryptoManager
from ..core.file_utils import FileManager
from ..utils.config import APP_NAME

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
        
        # Başlık
        self.lbl_head = ctk.CTkLabel(self, text="Klasör İşlemleri", font=("Roboto", 20, "bold"))
        self.lbl_head.grid(row=0, column=0, pady=20)

        # Klasör Seçim Çerçevesi
        self.frame_select = ctk.CTkFrame(self)
        self.frame_select.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_select.grid_columnconfigure(0, weight=1)

        self.lbl_folder = ctk.CTkLabel(self.frame_select, textvariable=self.master.selected_folder, wraplength=400)
        self.lbl_folder.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.btn_browse = ctk.CTkButton(self.frame_select, text="Klasör Seç", command=self.browse_folder, width=100)
        self.btn_browse.grid(row=0, column=1, padx=10, pady=10)

        # İşlem Butonları
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.grid(row=2, column=0, pady=20)

        self.btn_encrypt = ctk.CTkButton(self.frame_actions, text="🔒 ŞİFRELE", command=lambda: self.start_process('encrypt'), 
                                         fg_color="#d32f2f", hover_color="#b71c1c", width=150, height=40)
        self.btn_encrypt.pack(side="left", padx=10)

        self.btn_decrypt = ctk.CTkButton(self.frame_actions, text="🔓 ŞİFRE ÇÖZ", command=lambda: self.start_process('decrypt'), 
                                         fg_color="#388e3c", hover_color="#2e7d32", width=150, height=40)
        self.btn_decrypt.pack(side="left", padx=10)

        # Durum ve Progress
        self.lbl_status = ctk.CTkLabel(self, textvariable=self.master.status_text, text_color="cyan")
        self.lbl_status.grid(row=3, column=0, pady=(10, 0))

        self.progressbar = ctk.CTkProgressBar(self, width=400)
        self.progressbar.grid(row=4, column=0, pady=10)
        self.progressbar.set(0)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.master.selected_folder.set(folder)

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
