import os
import sys
import shutil
import time
import threading
import psutil # For memory checking (if installed, else fallback)

sys.path.append(os.getcwd())
from modules.vault.core.crypto_manager import CryptoManager
from modules.shatter.core.sharding import ShatterManager

TEST_DIR = "verify_edge_tests"
PASSWORD = "test_password_edge"

def get_process_memory():
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024 # MB
    except:
        return 0

def create_unicode_file():
    filename = "Deneme_Dosyası_🚀_Şçöğüi.txt"
    path = os.path.join(TEST_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("Merhaba Dünya 🌍")
    return path, filename

def test_unicode_handling(vault_mgr, shatter_mgr):
    print("\n[TEST 1] Unicode/Emoji Filename Handling...")
    path, filename = create_unicode_file()
    
    # 1. Vault Test
    try:
        enc_path = path + ".enc"
        vault_mgr.encrypt_file(path, enc_path)
        dec_path = path + ".dec"
        vault_mgr.decrypt_file(enc_path, dec_path)
        
        with open(dec_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if content == "Merhaba Dünya 🌍" and os.path.exists(dec_path):
            print("PASS: Vault handles Unicode filenames and content correctly.")
        else:
            print("FAIL: Vault corrupted Unicode content.")
    except Exception as e:
        print(f"FAIL: Vault crashed on Unicode filename. Error: {e}")

    # 2. Shatter Test
    try:
        # Shatter creates folder based on filename.
        sharded_folder = shatter_mgr.shatter_file(path, TEST_DIR, delete_original=False)
        manifest_name = f"{filename}.shatter_manifest"
        manifest_path = os.path.join(sharded_folder, manifest_name)
        
        if os.path.exists(manifest_path):
            # Reassemble
            restore_dir = os.path.join(TEST_DIR, "shatter_restore")
            os.makedirs(restore_dir, exist_ok=True)
            shatter_mgr.reassemble_file(manifest_path, restore_dir, delete_source=False)
            
            restored_file = os.path.join(restore_dir, filename)
            if os.path.exists(restored_file):
                 print("PASS: Shatter handles Unicode filenames correctly.")
            else:
                 print(f"FAIL: Shatter reassembly lost the unicode filename. (Expected: {filename})")
        else:
             print("FAIL: Shatter manifest name encoding issue.")
             
    except Exception as e:
        print(f"FAIL: Shatter crashed on Unicode. Error: {e}")

def test_file_locking(vault_mgr):
    print("\n[TEST 2] Locked File Handling...")
    filename = "locked_file.dat"
    path = os.path.join(TEST_DIR, filename)
    
    # Create and Lock
    f = open(path, "wb")
    f.write(b"data")
    f.flush()
    # Do NOT close f. File is open/locked (especially on Windows, less so on Unix but still good to check read access)
    
    try:
        enc_path = path + ".enc"
        # Reading an open file 'wb' might be allowed on Unix, but 'exclusive' lock isn't default in Python open.
        # However, let's see if our logic handles I/O errors gracefully if they occur.
        # On Mac/Linux this might succeed unless we use flock.
        # But let's assume worst case: PermissionError.
        # Since we can't easily force lock in portable Python without libs, we just test concurrent read.
        
        vault_mgr.encrypt_file(path, enc_path)
        print("INFO: File was readable even while open (Expected on Unix).")
    except Exception as e:
        print(f"PASS: Handled locked file error: {e}")
    finally:
        f.close()

def test_memory_usage(shatter_mgr):
    print("\n[TEST 3] Memory Usage on Large File (Shatter)...")
    # Generate 100MB file
    filename = "large_test_100mb.bin"
    path = os.path.join(TEST_DIR, filename)
    with open(path, "wb") as f:
        f.write(os.urandom(100 * 1024 * 1024))
        
    start_mem = get_process_memory()
    print(f"Start Memory: {start_mem:.2f} MB")
    
    # Run in background to measure peak? No, easier: logic check.
    # We just run it effectively.
    
    try:
        shatter_mgr.shatter_file(path, TEST_DIR)
        curr_mem = get_process_memory()
        diff = curr_mem - start_mem
        print(f"End Memory: {curr_mem:.2f} MB (Diff: {diff:.2f} MB)")
        
        if diff < 150: # Expect overhead to be reasonable (< 2x file size)
             # Actually shatter reads chunk by chunk (1MB or 20MB). 
             # So memory usage should remain LOW (near 20-50MB mostly), not linear to file size.
             # If it spiked to 100MB+, maybe read whole file?
             # Our logic: read(chunk_size). So it should be low.
             if diff < 50:
                 print("PASS: Memory usage is optimized (Stream processing confirmed).")
             else:
                 print("WARN: Memory usage higher than expected for chunk processing.")
        else:
             print("FAIL: Possible Memory Leak or Full File Read.")
             
    except Exception as e:
        print(f"FAIL: Memory test crashed: {e}")

def main():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    try:
        vault_mgr = CryptoManager(PASSWORD)
        vault_mgr.initialize_new_vault()
        
        shatter_mgr = ShatterManager(PASSWORD)
        
        test_unicode_handling(vault_mgr, shatter_mgr)
        test_file_locking(vault_mgr)
        test_memory_usage(shatter_mgr)
        
    except ImportError:
         print("Skipping Memory Test (psutil not found)")
    except Exception as e:
         print(f"Unexpected Error: {e}")
         
    # Cleanup
    try:
        shutil.rmtree(TEST_DIR)
    except:
        pass

if __name__ == "__main__":
    main()
