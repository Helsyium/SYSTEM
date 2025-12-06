import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import time
import subprocess
import platform

# Import Core Logic
from ..core.sharding import ShatterManager
from system.core.config import THEME

# DnD Completely Removed per user request
DND_FILES = None

print("DEBUG: LOADING MODULES.SHATTER.GUI.APP (Version 3.5 CLEAN FIX)")

class ShatterApp(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        
        print(f"DEBUG: ShatterApp init started with master={master}")
        try:
            self.title("SHATTER - Secure File Sharding")
            self.geometry("800x650") 
            self.resizable(False, False)
            
            self.configure(fg_color=THEME["colors"]["bg_main"])
            
            self.shatter_manager = None
            self.is_processing = False
            self.last_shatter_output = None
            self.last_reassemble_output = None
            
            # Grid Layout
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(1, weight=1)
            
            # Header
            self.create_header()
            
            # Main Content (Tab View: Shatter vs Reassemble)
            self.create_tabs()
            
            print("DEBUG: ShatterApp init finished")
            
        except Exception as e:
            print(f"CRITICAL ERROR in ShatterApp Init: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Kritik Hata", f"Pencere oluşturulurken hata: {e}")
            self.destroy()

    def create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        title = ctk.CTkLabel(header_frame, text="PROJECT SHATTER", font=("Roboto", 24, "bold"), text_color=THEME["colors"]["accent"])
        title.pack(side="left")
        
        subtitle = ctk.CTkLabel(header_frame, text="|  Military Grade Sharding Engine", font=("Roboto", 14), text_color=THEME["colors"]["text_secondary"])
        subtitle.pack(side="left", padx=10, pady=(5,0))
        
        # Theme Switch
        self.switch_theme = ctk.CTkSwitch(header_frame, text="Dark Mode", command=self.toggle_theme, onvalue="Dark", offvalue="Light")
        self.switch_theme.select() # Default Dark
        self.switch_theme.pack(side="right")

    def toggle_theme(self):
        mode = self.switch_theme.get()
        ctk.set_appearance_mode(mode)

    def create_tabs(self):
        self.tab_view = ctk.CTkTabview(self, fg_color="transparent")
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.tab_shatter = self.tab_view.add("SHATTER (Parçala)")
        self.tab_reassemble = self.tab_view.add("REASSEMBLE (Birleştir)")
        
        self.setup_shatter_tab()
        self.setup_reassemble_tab()



    def setup_shatter_tab(self):
        # File Selection Frame
        self.frame_files = ctk.CTkFrame(self.tab_shatter, fg_color="transparent")
        self.frame_files.pack(pady=10, fill="x", padx=10)
        
        btn_select = ctk.CTkButton(self.frame_files, text="DOSYALARI SEÇ (Batch)", command=self.select_files_shatter,
                                   fg_color=THEME["colors"]["accent"], text_color="black")
        btn_select.pack(pady=5, fill="x")

        # Folder Select Button (New)
        btn_select_folder = ctk.CTkButton(self.frame_files, text="KLASÖR SEÇ (Tümünü Parçala)", command=self.select_folder_shatter,
                                   fg_color=THEME["colors"]["accent"], text_color="black")
        btn_select_folder.pack(pady=5, fill="x")
        
        # Queue List (Using CTkTextbox as a read-only list since CTkListbox is not standard)
        self.queue_display = ctk.CTkTextbox(self.tab_shatter, height=100, width=500)
        self.queue_display.pack(pady=5)
        self.queue_display.insert("0.0", "Dosya veya Klasör seçilmedi...\n")
        
        self.queue_display.configure(state="disabled")
        
        self.selected_files = [] # List of paths
        
        # Password Input
        self.entry_pwd_shatter = ctk.CTkEntry(self.tab_shatter, placeholder_text="Şifre Belirle", show="*")
        self.entry_pwd_shatter.pack(pady=10)
        
        # Secure Delete Checkbox
        self.chk_secure_delete = ctk.CTkCheckBox(self.tab_shatter, text="Orijinal Dosyaları Sil (Secure Wipe)", 
                                                 text_color=THEME["colors"]["text_primary"], hover_color=THEME["colors"]["danger"])
        self.chk_secure_delete.pack(pady=5)
        
        # Action Button
        self.btn_shatter = ctk.CTkButton(self.tab_shatter, text="HEPSİNİ PARÇALA", command=self.run_shatter_batch,
                                         fg_color=THEME["colors"]["danger"], hover_color="#b71c1c", width=200, height=40)
        self.btn_shatter.pack(pady=20)
        
        # OPEN FOLDER BUTTON (Initially Hidden)
        self.btn_open_folder_shatter = ctk.CTkButton(self.tab_shatter, text="📂 SONUÇ KLASÖRÜNÜ AÇ", command=lambda: self.open_folder(self.last_shatter_output),
                                                     fg_color=THEME["colors"]["success"], width=200)
        
        # Overall Status
        self.lbl_overall_status = ctk.CTkLabel(self.tab_shatter, text="Hazır", font=("Roboto", 14, "bold"))
        self.lbl_overall_status.pack()
        
        # Progress
        self.progress_shatter = ctk.CTkProgressBar(self.tab_shatter, width=400)
        self.progress_shatter.pack(pady=5)
        self.progress_shatter.set(0)
        
        self.status_shatter = ctk.CTkLabel(self.tab_shatter, text="")
        self.status_shatter.pack()



    def setup_reassemble_tab(self):
        # 1. File Selection Buttons (Top, similar to Shatter Tab)
        self.frame_btns_reassemble = ctk.CTkFrame(self.tab_reassemble, fg_color="transparent")
        self.frame_btns_reassemble.pack(pady=10, fill="x", padx=10)
        
        btn_select_man = ctk.CTkButton(self.frame_btns_reassemble, text="MANIFEST SEÇ (Tek Dosya)", command=self.select_manifest,
                                       fg_color=THEME["colors"]["accent"], text_color="black")
        btn_select_man.pack(pady=5, fill="x")
        
        btn_select_dir = ctk.CTkButton(self.frame_btns_reassemble, text="KLASÖR SEÇ (Otomatik Tara)", command=self.select_folder_reassemble,
                                       fg_color=THEME["colors"]["accent"], text_color="black")
        btn_select_dir.pack(pady=5, fill="x")
        
        # 2. Queue List
        self.queue_reassemble = ctk.CTkTextbox(self.tab_reassemble, height=100, width=500)
        self.queue_reassemble.pack(pady=5)
        self.queue_reassemble.insert("0.0", "Manifest dosyasını seçin...\n")
        self.queue_reassemble.configure(state="disabled")
        
        self.selected_manifests = []
        
        # 3. Password Input
        self.entry_pwd_reassemble = ctk.CTkEntry(self.tab_reassemble, placeholder_text="Şifre Girin", show="*")
        self.entry_pwd_reassemble.pack(pady=10)
        
        # 4. Action Button (Cool Style)
        self.btn_reassemble = ctk.CTkButton(self.tab_reassemble, text="BİRLEŞTİR VE ÇÖZ", command=self.run_reassemble_batch,
                                            fg_color=THEME["colors"]["success"], hover_color="#00c853", 
                                            width=200, height=40, font=("Roboto", 16, "bold"))
        self.btn_reassemble.pack(pady=20)
        
        # OPEN FOLDER BUTTON (Initially Hidden)
        self.btn_open_folder_reassemble = ctk.CTkButton(self.tab_reassemble, text="📂 SONUÇ KLASÖRÜNÜ AÇ", command=lambda: self.open_folder(self.last_reassemble_output),
                                                        fg_color=THEME["colors"]["accent"], width=200)

        # Overall Status
        self.lbl_reassemble_status = ctk.CTkLabel(self.tab_reassemble, text="Hazır", font=("Roboto", 14, "bold"))
        self.lbl_reassemble_status.pack()

        # Progress
        self.progress_reassemble = ctk.CTkProgressBar(self.tab_reassemble, width=400)
        self.progress_reassemble.pack(pady=5)
        self.progress_reassemble.set(0)
        
        self.status_reassemble = ctk.CTkLabel(self.tab_reassemble, text="")
        self.status_reassemble.pack()



    def open_folder(self, path):
        if not path or not os.path.exists(path):
            return
        if os.path.isfile(path):
            path = os.path.dirname(path)
            
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı: {e}")

    # --- Actions ---

    def select_files_shatter(self):
        paths = filedialog.askopenfilenames()
        if paths:
            # Append instead of replace to allow mixing
            for p in paths:
                if p not in self.selected_files:
                    self.selected_files.append(p)
            self.update_queue_display()

    def select_folder_shatter(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            # Scan directory for files
            # Ignore hidden files, system files, and existing _sharded folders
            count = 0
            for root, dirs, files in os.walk(folder_path):
                # Skip _sharded directories
                if "_sharded" in root:
                    continue
                
                for file in files:
                    if file.startswith("."): continue # Skip hidden
                    if file.endswith(".DS_Store"): continue
                    
                    full_path = os.path.join(root, file)
                    if full_path not in self.selected_files:
                        self.selected_files.append(full_path)
                        count += 1
            
            messagebox.showinfo("Bilgi", f"Klasörden {count} dosya eklendi.")
            self.update_queue_display()

    def update_queue_display(self):
        self.queue_display.configure(state="normal")
        self.queue_display.delete("0.0", "end")
        for p in self.selected_files:
            self.queue_display.insert("end", f"• {os.path.basename(p)}\n")
        self.queue_display.configure(state="disabled")
        
    def select_manifest(self):
        path = filedialog.askopenfilename(filetypes=[("Shatter Manifest", "*.shatter_manifest")])
        if path:
            # CRITICAL FIX: Ignore macOS resource fork files (._*)
            if os.path.basename(path).startswith("._"):
                messagebox.showerror("Hata", "Lütfen '._' ile başlayan dosyayı DEĞİL, gerçek manifest dosyasını seçin.")
                return
                
            self.selected_manifests = [path]
            self.update_reassemble_queue_display()
            
    def select_folder_reassemble(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            # Scan for manifests
            # We need a temporary manager instance or move scan method to static/helper
            # For simplicity, just check manually or init manager dummy
            # Or better, instantiation is cheap.
            try:
                # We don't need password for scanning
                manager = ShatterManager(password="dummy") 
                manifests = manager.scan_directory_for_manifests(folder_path)
                if not manifests:
                    messagebox.showinfo("Bilgi", "Bu klasörde manifest dosyası bulunamadı.")
                    return
                
                self.selected_manifests = manifests
                self.update_reassemble_queue_display()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Tarama hatası: {e}")

    def update_reassemble_queue_display(self):
        self.queue_reassemble.configure(state="normal")
        self.queue_reassemble.delete("0.0", "end")
        for p in self.selected_manifests:
            self.queue_reassemble.insert("end", f"• {os.path.basename(p)}\n")
        self.queue_reassemble.configure(state="disabled")

    def run_shatter_batch(self):
        if not self.selected_files:
            messagebox.showerror("Hata", "Lütfen en az bir dosya seçin.")
            return
        
        pwd = self.entry_pwd_shatter.get()
        if len(pwd) < 4:
            messagebox.showerror("Hata", "Şifre en az 4 karakter olmalı.")
            return
            
        delete_original = self.chk_secure_delete.get() == 1
            
        self.is_processing = True
        self.btn_shatter.configure(state="disabled", text="İŞLENİYOR...")
        self.btn_open_folder_shatter.pack_forget() # Hide previous open button
        self.progress_shatter.set(0)
        
        thread = threading.Thread(target=self._process_shatter_batch, args=(self.selected_files, pwd, delete_original))
        thread.start()

    def _process_shatter_batch(self, files, password, delete_original):
        last_output = None
        try:
            manager = ShatterManager(password)
            total_files = len(files)
            
            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                # self.lbl_overall_status.configure(text=f"İşleniyor: {i+1}/{total_files} - {filename}")
                # UI update thread-safe wrap if needed, but ctk usually ok
                
                def cb(percent, msg):
                    self.progress_shatter.set(percent / 100)
                    self.status_shatter.configure(text=msg)
                
                # Execute Shatter for single file
                output_folder = manager.shatter_file(file_path, callback=cb, delete_original=delete_original)
                last_output = output_folder
                print(f"Finished: {output_folder}")
            
            self.lbl_overall_status.configure(text="Tüm İşlemler Tamamlandı!")
            self.status_shatter.configure(text="Sıra Bitti.")
            self.progress_shatter.set(1)
            
            self.last_shatter_output = last_output # Save for open button
            self.btn_open_folder_shatter.pack(pady=5) # Show open button
            
            messagebox.showinfo("Başarılı", f"{total_files} dosya başarıyla parçalandı.")
            
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            self.lbl_overall_status.configure(text="Hata Oluştu!")
        finally:
            self.is_processing = False
            self.btn_shatter.configure(state="normal", text="HEPSİNİ PARÇALA")

    def run_reassemble_batch(self):
        if not self.selected_manifests:
            messagebox.showerror("Hata", "Lütfen manifest veya klasör seçin.")
            return
        
        pwd = self.entry_pwd_reassemble.get()
        if not pwd:
            messagebox.showerror("Hata", "Şifre girin.")
            return
            
        # Ask for Output Directory
        # Default: Parent of the first manifest's folder
        initial_dir = os.path.dirname(os.path.dirname(self.selected_manifests[0]))
        output_dir = filedialog.askdirectory(title="Dosyalar Nereye Çıkartılsın?", initialdir=initial_dir)
        
        if not output_dir:
            return  # Cancelled
            
        self.is_processing = True
        self.btn_reassemble.configure(state="disabled", text="ÇÖZÜLÜYOR...")
        self.btn_open_folder_reassemble.pack_forget() # Hide previous
        self.progress_reassemble.set(0)
        
        thread = threading.Thread(target=self._process_reassemble_batch, args=(self.selected_manifests, pwd, output_dir))
        thread.start()

    def _process_reassemble_batch(self, manifests, password, output_dir):
        try:
            manager = ShatterManager(password)
            total_files = len(manifests)
            
            for i, manifest_path in enumerate(manifests):
                filename = os.path.basename(manifest_path)
                # self.lbl_reassemble_status.configure(text=f"Birleştiriliyor: {i+1}/{total_files} - {filename}")
                
                def cb(percent, msg):
                    self.progress_reassemble.set(percent / 100)
                    self.status_reassemble.configure(text=msg)
                
                # output_dir passed, delete_source=True used by default for cleanup
                output_path = manager.reassemble_file(manifest_path, output_dir=output_dir, callback=cb, delete_source=True)
            
            self.lbl_reassemble_status.configure(text="Tamamlandı!")
            self.status_reassemble.configure(text="Sıra Bitti.")
            
            self.last_reassemble_output = output_dir
            self.btn_open_folder_reassemble.pack(pady=5)
            
            messagebox.showinfo("Başarılı", f"{total_files} dosya başarıyla birleştirildi ve temizlendi.")
            
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            self.lbl_reassemble_status.configure(text="Hata!")
        finally:
            self.is_processing = False
            self.btn_reassemble.configure(state="normal", text="BİRLEŞTİR VE ÇÖZ")
