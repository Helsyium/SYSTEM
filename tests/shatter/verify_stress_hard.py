
import os
import secrets
import struct
import base64
import uuid
import sys
import shutil
import time

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from modules.shatter.core.crypto import ShatterCrypto
from modules.shatter.core.sharding import ShatterManager

def test_nonce_collision_stress(iterations=100000):
    print(f"\n[5.1] Nonce Collision Stress Test ({iterations} iterations)...")
    crypto = ShatterCrypto("stress_test")
    key = secrets.token_bytes(32)
    
    seen_nonces = set()
    start_time = time.time()
    
    for i in range(iterations):
        # Using struct.pack to simulate chunk indices ensuring unique input context
        context = struct.pack("<Q", i)
        nonce = crypto.derive_deterministic_nonce(key, context)
        
        if nonce in seen_nonces:
            print(f"❌ FAIL: Collision detected at index {i}!")
            return False
        seen_nonces.add(nonce)
        
    duration = time.time() - start_time
    print(f"✅ PASS: No collisions in {iterations} nonces. (Time: {duration:.2f}s)")
    return True

def test_key_wrap_ad_stress():
    print(f"\n[5.2] Key-Wrap AD (Context) Integrity Test...")
    crypto = ShatterCrypto("stress_test")
    master_key = secrets.token_bytes(32)
    chunk_key = secrets.token_bytes(32)
    
    correct_uuid = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    wrong_uuid =   "f1e2d3c4-b5a6-0987-4321-098765fedcba"
    
    # 1. Wrap with Correct UUID
    wrapped = crypto.wrap_key(master_key, chunk_key, context=correct_uuid)
    
    # 2. Unwrap with Wrong UUID (Should Fail)
    try:
        crypto.unwrap_key(master_key, wrapped, context=wrong_uuid)
        print("❌ FAIL: Unwrap succeeded with wrong AD!")
        return False
    except Exception:
        pass # Expected
        
    # 3. Unwrap with Correct UUID (Should Succeed)
    try:
        unwrapped = crypto.unwrap_key(master_key, wrapped, context=correct_uuid)
        if unwrapped != chunk_key:
            print("❌ FAIL: Unwrap result mismatch!")
            return False
    except Exception as e:
        print(f"❌ FAIL: Valid unwrap failed: {e}")
        return False
        
    print("✅ PASS: AEAD Context Binding checks out.")
    return True

def test_tampering_stress(manager):
    print(f"\n[5.3] Tampering Stress Test...")
    test_file = "stress_data.bin"
    # Create 1MB dummy
    with open(test_file, "wb") as f:
        f.write(secrets.token_bytes(1024 * 1024))
        
    sharded_dir = manager.shatter_file(test_file, delete_original=False)
    manifest_path = os.path.join(sharded_dir, f"{test_file}{manager.MANIFEST_EXT}")
    
    # CASE 1: Modify 1 byte of Manifest Ciphertext
    print("  -> Corrupting Manifest Ciphertext...")
    with open(manifest_path, "rb") as f:
        data = f.read()
    
    # Change last byte
    corrupt_data = data[:-1] + bytes([data[-1] ^ 0xFF])
    
    with open(manifest_path, "wb") as f:
        f.write(corrupt_data)

    output_tmp = "stress_out_1"
    os.makedirs(output_tmp, exist_ok=True)
    
    try:
        manager.reassemble_file(manifest_path, output_dir=output_tmp, delete_source=False)
        print("❌ FAIL: Decrypted corrupted manifest!")
        shutil.rmtree(sharded_dir)
        shutil.rmtree(output_tmp)
        os.remove(test_file)
        return False
    except ValueError as e:
        print(f"  -> Caught expected error (Manifest Integrity): {e}")

    # Restore Code: In a real scenario we'd use .bak, but here we just re-shatter or use .bak manually
    # Let's verify .bak is untouched and working
    backup_path = manifest_path + ".bak"
    try:
        manager.reassemble_file(backup_path, output_dir=output_tmp, delete_source=False)
        print("  -> Backup (.bak) worked successfully.")
    except Exception as e:
        print(f"❌ FAIL: Backup failed: {e}")
        return False

    shutil.rmtree(output_tmp)
    shutil.rmtree(sharded_dir)
    os.remove(test_file)
    
    print("✅ PASS: Tampering detection works.")
    return True

if __name__ == "__main__":
    print("🧪 running FINAL STRESS & SECURITY AUDIT SUITE...")
    manager = ShatterManager("StressPass")
    
    if not test_nonce_collision_stress(100000): exit(1)
    if not test_key_wrap_ad_stress(): exit(1)
    if not test_tampering_stress(manager): exit(1)
    
    print("\n🏆 ALL CRITICAL SECURITY TESTS PASSED. SYSTEM IS ROBUST.")
