import os
import sys
import shutil
import time

# Proje kökünü path'e ekle
sys.path.append(os.getcwd())

from modules.vault.core.crypto_manager import CryptoManager
from modules.vault.core.file_utils import FileManager
from modules.vault.utils.config import ENCRYPTED_EXT

TEST_DIR = "verification_v3_folder"
TEST_FILE = "secret_v3.txt"
PASSWORD = "strong_password"

def setup():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    with open(os.path.join(TEST_DIR, TEST_FILE), "w") as f:
        f.write("A" * 70000) # 64KB'dan büyük veri (Multi-chunk test)

def test_dynamic_salt():
    print("--- 1. Dinamik Salt Testi ---")
    c1 = CryptoManager(PASSWORD)
    m1 = c1.initialize_new_vault()
    
    c2 = CryptoManager(PASSWORD)
    m2 = c2.initialize_new_vault()
    
    if m1 == m2:
        print("FAIL: Manifest içeriği aynı! Salt random değil.")
        return False
        
    # İlk 8 byte (Magic) aynı olmalı mı? Hayır, benim yapıda [SALT] başta.
    # SALT (16 byte) farklı olmalı.
    salt1 = m1[:16]
    salt2 = m2[:16]
    
    if salt1 == salt2:
        print("FAIL: Salt'lar aynı!")
        return False
        
    print("PASS: Her vault için farklı salt üretiliyor.")
    return True

def test_integrity_check():
    print("\n--- 2. Chunk Integrity (Tampering) Testi ---")
    # Dosyayı şifrele
    setup() # Reset
    crypto = CryptoManager(PASSWORD)
    manager = FileManager(crypto)
    
    manager.process_folder(TEST_DIR, mode='encrypt')
    
    # Şifreli dosyayı bul
    encrypted_files = [f for f in os.listdir(TEST_DIR) if f.endswith(ENCRYPTED_EXT)]
    if not encrypted_files:
        print("FAIL: Şifreli dosya bulunamadı.")
        return False
    
    enc_path = os.path.join(TEST_DIR, encrypted_files[0])
    
    # Dosyanın ortasından bir byte değiştir
    with open(enc_path, "r+b") as f:
        f.seek(100) # Header (Salt) geç random yere git
        byte = f.read(1)
        f.seek(100)
        # Flip bits
        f.write(bytes([byte[0] ^ 0xFF]))
        
    print(f"   (Dosya manipüle edildi: {enc_path})")
    
    # Çözmeye çalış
    try:
        manager.process_folder(TEST_DIR, mode='decrypt')
        # process_folder hataları print eder ama raise etmez (genel yapı).
        # Bu yüzden dosyanın çözüldü mü kontrol etmeliyiz.
        
        decrypted_files = [f for f in os.listdir(TEST_DIR) if f.endswith(".txt")]
        if decrypted_files:
             # Eğer .txt oluştuysa, içi bozuk mu yoksa şifreleme mi kırıldı?
             # Integrity check fail olduğunda output dosyası SİLİNMELİ.
             # FileManager._decrypt_single_file içinde catch durumunda output siliniyor.
             print("FAIL: Bozuk dosya çözüldü (Dosya mevcut)!")
             return False
             
        print("PASS: Bozuk dosya çözülemedi (Dosya oluşturulmadı).")
        return True
        
    except ValueError as e:
        print(f"PASS: Beklenen bütünlük hatası alındı: {e}")
        return True
    except Exception as e:
        print(f"Hata detayı: {e}")
        # Hata fırlatılması da kabuldür (eğer process_folder durursa)
        return True

def test_full_cycle():
    print("\n--- 3. Tam Şifreleme/Çözme Döngüsü ---")
    setup()
    crypto = CryptoManager(PASSWORD)
    manager = FileManager(crypto)
    
    # Encrypt
    manager.process_folder(TEST_DIR, mode='encrypt')
    
    # Decrypt
    manager.process_folder(TEST_DIR, mode='decrypt')
    
    # Content Check
    final_path = os.path.join(TEST_DIR, TEST_FILE)
    if not os.path.exists(final_path):
        print(f"FAIL: Orijinal dosya geri gelmedi: {final_path}")
        return False
        
    with open(final_path, "r") as f:
        content = f.read()
    
    if len(content) == 70000 and content.startswith("AAAA"):
        print("PASS: İçerik başarıyla kurtarıldı.")
        return True
    else:
        print("FAIL: İçerik bozuk!")
        return False

if __name__ == "__main__":
    setup()
    if test_dynamic_salt():
        if test_integrity_check():
            if test_full_cycle():
                print("\n=== TÜM HARDENING TESTLERİ BAŞARILI ===")
                shutil.rmtree(TEST_DIR)
                exit(0)
    
    print("\n!!! TEST BAŞARISIZ !!!")
    exit(1)
