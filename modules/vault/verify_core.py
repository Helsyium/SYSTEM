import os
import sys
import shutil

# Proje kök dizinini path'e ekle
sys.path.append(os.getcwd())

from modules.vault.core.crypto_manager import CryptoManager
from modules.vault.core.file_utils import FileManager
from modules.vault.utils.config import ENCRYPTED_EXT

TEST_DIR = "verification_test_folder"
TEST_FILE = "secret_data.txt"
PASSWORD = "strong_password_123"
CONTENT = b"Bu cok gizli bir veridir. Antigravity tarafindan korunmaktadir."

def setup():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    with open(os.path.join(TEST_DIR, TEST_FILE), "wb") as f:
        f.write(CONTENT)
    
    # Alt klasör testi
    os.makedirs(os.path.join(TEST_DIR, "subdir"))
    with open(os.path.join(TEST_DIR, "subdir", "subfile.txt"), "wb") as f:
        f.write(CONTENT)

def test_encryption():
    print("--- Şifreleme Testi Başlıyor ---")
    crypto = CryptoManager(PASSWORD)
    manager = FileManager(crypto)
    
    manager.process_folder(TEST_DIR, mode='encrypt')
    
    # 1. Orijinal dosya silindi mi?
    if os.path.exists(os.path.join(TEST_DIR, TEST_FILE)):
        print("FAIL: Orijinal dosya silinmedi!")
        return False
        
    # 2. Şifreli dosya var mı? (İsmi değiştiği için listdir ile bakacağız)
    files = os.listdir(TEST_DIR)
    encrypted_files = [f for f in files if f.endswith(ENCRYPTED_EXT)]
    if not encrypted_files:
        print("FAIL: Şifreli dosya bulunamadı!")
        return False
    
    print(f"Şifreli dosyalar: {encrypted_files}")
    
    # 3. Alt klasör şifrelendi mi?
    subdirs = [d for d in files if os.path.isdir(os.path.join(TEST_DIR, d))]
    print(f"Şifreli klasörler: {subdirs}")
    if "subdir" in subdirs:
        print("FAIL: Alt klasör ismi şifrelenmedi!")
        return False
        
    print("PASS: Şifreleme başarılı görünüyor.")
    return True

def test_decryption():
    print("\n--- Deşifreleme Testi Başlıyor ---")
    crypto = CryptoManager(PASSWORD)
    manager = FileManager(crypto)
    
    manager.process_folder(TEST_DIR, mode='decrypt')
    
    # 1. Orijinal dosya geri geldi mi?
    target = os.path.join(TEST_DIR, TEST_FILE)
    if not os.path.exists(target):
        print(f"FAIL: {TEST_FILE} geri gelmedi!")
        # Mevcut dosyaları listele
        print("Mevcut:", os.listdir(TEST_DIR))
        return False
        
    # 2. İçerik doğru mu?
    with open(target, "rb") as f:
        data = f.read()
        if data != CONTENT:
            print("FAIL: İçerik bozuk!")
            return False
            
    # 3. Alt klasör geri geldi mi?
    if not os.path.exists(os.path.join(TEST_DIR, "subdir", "subfile.txt")):
        print("FAIL: Alt klasör/dosya geri gelmedi!")
        return False
        
    print("PASS: Deşifreleme başarılı ve veri bütünlüğü korundu.")
    return True

if __name__ == "__main__":
    setup()
    if test_encryption():
        if test_decryption():
            print("\n=== TÜM TESTLER BAŞARILI ===")
            # Temizlik
            shutil.rmtree(TEST_DIR)
        else:
            print("\n!!! DEŞİFRELEME BAŞARISIZ !!!")
            exit(1)
    else:
        print("\n!!! ŞİFRELEME BAŞARISIZ !!!")
        exit(1)
