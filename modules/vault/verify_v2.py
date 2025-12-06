import os
import sys
import shutil

# Proje kökünü path'e ekle
sys.path.append(os.getcwd())

from modules.vault.core.crypto_manager import CryptoManager
from modules.vault.core.file_utils import FileManager
from modules.vault.utils.config import ENCRYPTED_EXT

TEST_DIR = "verification_v2_folder"
TEST_FILE = "secret_v2.txt"
PASSWORD_1 = "correct_password"
PASSWORD_2 = "wrong_password"

def setup():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    with open(os.path.join(TEST_DIR, TEST_FILE), "w") as f:
        f.write("Secret Data")

def test_manifest_encryption():
    print("--- 1. Şifreleme ve Manifest Oluşturma Testi ---")
    crypto = CryptoManager(PASSWORD_1)
    manager = FileManager(crypto)
    
    manager.process_folder(TEST_DIR, mode='encrypt')
    
    manifest_path = os.path.join(TEST_DIR, ".vault_manifest")
    if not os.path.exists(manifest_path):
        print("FAIL: Manifest dosyası oluşturulmadı!")
        return False
        
    print("PASS: Manifest oluşturuldu.")
    return True

def test_wrong_password_decrypt():
    print("\n--- 2. Yanlış Şifre ile Çözme Testi ---")
    crypto = CryptoManager(PASSWORD_2) # Yanlış şifre
    manager = FileManager(crypto)
    
    try:
        manager.process_folder(TEST_DIR, mode='decrypt')
        print("FAIL: Yanlış şifreyle işlem yapılmasına izin verildi!")
        return False
    except ValueError as e:
        print(f"PASS: Beklenen hata yakalandı: {e}")
        return True

def test_wrong_password_double_encrypt():
    print("\n--- 3. Şifreli Klasörü Tekrar Şifreleme Testi (Yanlış Şifreyle) ---")
    # Şu an klasör şifreli (Password 1 ile).
    # Password 2 ile tekrar şifrelemeye çalışalım.
    crypto = CryptoManager(PASSWORD_2)
    manager = FileManager(crypto)
    
    try:
        manager.process_folder(TEST_DIR, mode='encrypt')
        print("FAIL: Şifreli klasörün tekrar şifrelenmesine izin verildi!")
        return False
    except ValueError as e:
        print(f"PASS: Beklenen hata yakalandı: {e}")
        return True

def test_correct_decrypt():
    print("\n--- 4. Doğru Şifre ile Çözme Testi ---")
    crypto = CryptoManager(PASSWORD_1)
    manager = FileManager(crypto)
    
    try:
        manager.process_folder(TEST_DIR, mode='decrypt')
        print("PASS: İşlem başarılı.")
        
        # Manifest silindi mi?
        manifest_path = os.path.join(TEST_DIR, ".vault_manifest")
        if os.path.exists(manifest_path):
            print("FAIL: Manifest dosyası silinmedi!")
            return False
            
        return True
    except Exception as e:
        print(f"FAIL: Beklenmeyen hata: {e}")
        return False

if __name__ == "__main__":
    setup()
    if test_manifest_encryption():
        if test_wrong_password_decrypt():
            if test_wrong_password_double_encrypt():
                if test_correct_decrypt():
                    print("\n=== TÜM V2 TESTLERİ BAŞARILI ===")
                    shutil.rmtree(TEST_DIR)
                    exit(0)
    
    print("\n!!! TEST BAŞARISIZ !!!")
    exit(1)
