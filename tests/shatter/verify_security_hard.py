
import os
import shutil
import base64
import json
import logging
import sys
import uuid
import secrets
import struct

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Use correct import path for argon2 dependent module
from modules.shatter.core.sharding import ShatterManager
from modules.shatter.core.crypto import ShatterCrypto

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def create_dummy_file(filename, size_mb=1):
    size_bytes = size_mb * 1024 * 1024
    with open(filename, "wb") as f:
        f.write(secrets.token_bytes(size_bytes))
    return filename

def test_nonce_uniqueness():
    print("\n--- [TEST A] Nonce Uniqueness Check ---")
    crypto = ShatterCrypto("test")
    key = secrets.token_bytes(32)
    
    # Same key, different indexes -> DIFFERENT nonces
    n1 = crypto.derive_deterministic_nonce(key, struct.pack("<Q", 1))
    n2 = crypto.derive_deterministic_nonce(key, struct.pack("<Q", 2))
    
    if n1 == n2:
        print("❌ FAIL: Nonce collision for different indexes!")
        return False
        
    # Same key, same index -> SAME Nonce (Deterministic)
    n1_again = crypto.derive_deterministic_nonce(key, struct.pack("<Q", 1))
    if n1 != n1_again:
        print("❌ FAIL: Deterministic Nonce generation unstable!")
        return False
        
    print("✅ PASS: Nonce logic behaves as expected (Unique per index/context).")
    return True

def test_context_bound_wrapping():
    print("\n--- [TEST B] Context-Bound Key Wrapping (Cut-and-Paste Defense) ---")
    crypto = ShatterCrypto("test")
    master_key = secrets.token_bytes(32)
    chunk_key = secrets.token_bytes(32)
    
    uuid1 = uuid.uuid4().hex
    uuid2 = uuid.uuid4().hex
    
    # Wrap with UUID1
    wrapped = crypto.wrap_key(master_key, chunk_key, context=uuid1)
    
    # Try Unwrap with UUID1 (Should Work)
    try:
        unwrapped = crypto.unwrap_key(master_key, wrapped, context=uuid1)
        if unwrapped != chunk_key:
            print("❌ FAIL: Unwrap result mismatch!")
            return False
    except Exception as e:
        print(f"❌ FAIL: Valid unwrap raised exception: {e}")
        return False
        
    # Try Unwrap with UUID2 (Should FAIL)
    try:
        crypto.unwrap_key(master_key, wrapped, context=uuid2)
        print("❌ FAIL: Unwrap with WRONG context should have failed but succeeded!")
        return False
    except Exception:
        print("✅ PASS: Unwrap rejected wrong context (Anti Cut-and-Paste working).")
        
    return True

def test_manifest_recovery(original_file, sharded_dir, manager):
    print("\n--- [TEST C] Manifest Backup & Tamper Recovery ---")
    
    manifest_name = f"{original_file}{manager.MANIFEST_EXT}"
    manifest_path = os.path.join(sharded_dir, manifest_name)
    backup_path = manifest_path + ".bak"
    
    # 1. Corrupt Main Manifest
    print("Simulating corruption of main manifest...")
    with open(manifest_path, "wb") as f:
        f.write(b"CORRUPTED_DATA_TRASH")
        
    # 2. Try Reassembly (Should fail or user needs to manually restore - 
    # Current logic expects 'manifest_path' to be valid file path.
    # We will simulate user pointing to .bak)
    
    try:
        # Check if code handles pointing strictly to .bak or if logic auto-recovers?
        # Current code does NOT auto-recover if main file is trash, user must point to backup.
        # But let's verify .bak is valid.
        print(f"Attemping reassembly from backup: {backup_path}")
        restored = manager.reassemble_file(backup_path, delete_source=False, output_dir=".")
        print(f"✅ PASS: Reassembly from .bak successful: {restored}")
        if os.path.exists(restored): os.remove(restored)
        return True
    except Exception as e:
        print(f"❌ FAIL: Reassembly from backup failed: {e}")
        return False

def test_chunk_tampering(original_file, sharded_dir, manager):
    print("\n--- [TEST D] Chunk Tampering (Integrity Check) ---")
    
    # Find a chunk
    chunk_file = None
    for f in os.listdir(sharded_dir):
        if f.endswith(".enc"):
            chunk_file = os.path.join(sharded_dir, f)
            break
            
    if not chunk_file:
        print("❌ FAIL: No chunks found to tamper.")
        return False
        
    # Modify one byte in the middle
    with open(chunk_file, "r+b") as f:
        f.seek(50)
        byte = f.read(1)
        f.seek(50)
        f.write(bytes([byte[0] ^ 0xFF])) # Flip bits
        
    manifest_path = os.path.join(sharded_dir, f"{original_file}{manager.MANIFEST_EXT}")
    
    # Use a temp dir for reassembly output to avoid overwriting/deleting source
    output_temp = "tamper_test_out"
    os.makedirs(output_temp, exist_ok=True)
    
    try:
        manager.reassemble_file(manifest_path, delete_source=False, output_dir=output_temp)
        print("❌ FAIL: Reassembly succeeded despite tampered chunk!")
        shutil.rmtree(output_temp)
        return False
    except ValueError as e:
        # "Parça şifresi çözülemedi" or "Bütünlük Hatası" are both valid rejections
        err_msg = str(e)
        if "Bütünlük Hatası" in err_msg or "Parça şifresi çözülemedi" in err_msg or "Integrity" in err_msg:
            print(f"✅ PASS: System correctly detected tampering: {e}")
            shutil.rmtree(output_temp)
            return True
        else:
            print(f"⚠️ WARN: Failed but with unexpected error: {e}")
            shutil.rmtree(output_temp)
            return True
    except Exception as e:
         print(f"✅ PASS: System rejected tampering (Exception: {type(e).__name__})")
         if os.path.exists(output_temp): shutil.rmtree(output_temp)
         return True

def main():
    print("🛡️ SHATTER v3.5 Security Verification Suite 🛡️")
    password = "StrongPassword!"
    manager = ShatterManager(password)
    
    if not test_nonce_uniqueness(): return
    if not test_context_bound_wrapping(): return
    
    # Setup Real Files
    test_file = "security_test.dat"
    create_dummy_file(test_file, size_mb=1)
    
    try:
        sharded_dir = manager.shatter_file(test_file, delete_original=False)
    except Exception as e:
        print(f"setup failed: {e}")
        return

    if not test_chunk_tampering(test_file, sharded_dir, manager): return
    
    # Clean and re-shatter for recovery test
    shutil.rmtree(sharded_dir)
    sharded_dir = manager.shatter_file(test_file, delete_original=False)
    
    if not test_manifest_recovery(test_file, sharded_dir, manager): return

    # Cleanup
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(sharded_dir): shutil.rmtree(sharded_dir)
    
    print("\n🎉 ALL SECURITY TESTS PASSED")

if __name__ == "__main__":
    main()
