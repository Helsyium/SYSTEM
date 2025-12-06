import os
import json
import base64
import uuid
import shutil
import concurrent.futures
import time
import secrets  # CRITICAL FIX for v3.5
from typing import List, Dict
from .crypto import ShatterCrypto

class ShatterManager:
    """
    Dosya Parçalama ve Birleştirme Yöneticisi.
    """
    CHUNK_SIZE = 1024 * 1024 # 1 MB
    MANIFEST_EXT = ".shatter_manifest"
    CHUNK_EXT_PREFIX = ".part" # Deprecated usage for filename, but kept for legacy checks if needed
    ENCRYPTED_CHUNK_EXT = ".enc"
    
    def __init__(self, password: str):
        self.crypto = ShatterCrypto(password)
        
    def _calculate_chunk_size(self, file_size: int) -> int:
        """Dosya boyutuna göre ideal parça boyutunu hesaplar."""
        MB = 1024 * 1024
        
        if file_size < 100 * MB:
            return 1 * MB     # < 100 MB -> 1 MB chunks
        elif file_size < 1 * 1024 * MB:
            return 5 * MB     # < 1 GB -> 5 MB chunks
        elif file_size < 10 * 1024 * MB:
            return 20 * MB    # < 10 GB -> 20 MB chunks
        else:
            return 50 * MB    # > 10 GB -> 50 MB chunks

    def _secure_delete(self, file_path: str):
        """
        Dosyayı güvenli bir şekilde siler (Overwrite + Remove).
        UYARI: SSD/Flash depolamada 'Wear Leveling' nedeniyle verinin fiziksel olarak
        silindiği garanti edilemez. Ancak şifreleme anahtarları yok edildiği için
        dosya kurtarılsa bile şifreli kalır (Cryptographic Erasure).
        """
        if not os.path.exists(file_path):
            return
            
        print(f"Bilgi: Güvenli silme yapılıyor: {os.path.basename(file_path)} (Not: SSD'lerde kriptografik silme esastır)")
        
        length = os.path.getsize(file_path)
        with open(file_path, "wb") as f:
            # 1. Pass: Random Data
            f.write(secrets.token_bytes(length))
            f.flush()
            os.fsync(f.fileno())
            
        os.remove(file_path)

    def shatter_file(self, file_path: str, output_dir: str = None, callback=None, delete_original: bool = False):
        """
        Dosyayı parçalar, şifreler ve manifest oluşturur.
        Çıktılar 'DosyaAdi_sharded' klasörüne yazılır.
        delete_original=True ise işlem başarılı olduğunda orijinal dosya silinir.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        if output_dir is None:
            output_dir = os.path.dirname(file_path)
            
        # Create Output Directory: Filename_sharded
        target_folder_name = filename + "_sharded"
        target_folder_path = os.path.join(output_dir, target_folder_name)
        os.makedirs(target_folder_path, exist_ok=True)
            
        # Dynamic Chunk Size
        chunk_size = self._calculate_chunk_size(file_size)
            
        # Manifest Verisi Hazırlığı
        manifest_data = {
            "version": 2.5, # Version bumped for UUID support
            "original_filename": filename,
            "original_size": file_size,
            "chunk_size": chunk_size,
            "chunks": []
        }
        
        chunk_index = 0
        total_chunks = (file_size // chunk_size) + (1 if file_size % chunk_size > 0 else 0)
        
        with open(file_path, "rb") as f:
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                # 1. Unique Key Generate
                chunk_key = self.crypto.generate_chunk_key()
                
                # 2. Calculate Hash (Plaintext)
                chunk_hash = self.crypto.calculate_hash(chunk_data)
                
                # 3. Encrypt Chunk
                nonce, ciphertext = self.crypto.encrypt_chunk(chunk_data, chunk_key)
                
                # 4. Write Encrypted Chunk to Disk
                # v2.5 Change: Use UUID for filename obfuscation
                chunk_uuid = uuid.uuid4().hex
                chunk_filename = f"{chunk_uuid}{self.ENCRYPTED_CHUNK_EXT}"
                
                # Save into the sharded folder
                chunk_path = os.path.join(target_folder_path, chunk_filename)
                
                with open(chunk_path, "wb") as cf:
                    cf.write(nonce + ciphertext)
                
                # 5. Add to Manifest
                manifest_data["chunks"].append({
                    "index": chunk_index,
                    "filename": chunk_filename,
                    "key": base64.b64encode(chunk_key).decode('utf-8'),
                    "hash": chunk_hash
                })
                
                chunk_index += 1
                if callback:
                    progress = (chunk_index / total_chunks) * 100
                    callback(progress, f"Parçalanıyor ({chunk_size//1024//1024}MB Chunks): {chunk_index}/{total_chunks}")
                    
        # 6. Save Encrypted Manifest inside the folder (and backup)
        self._save_manifest(manifest_data, target_folder_path, filename)
        
        # 7. Secure Delete (If requested)
        if delete_original:
            if callback: callback(1.0, "Orijinal dosya güvenli siliniyor...")
            self._secure_delete(file_path)
        
        return target_folder_path

    def _write_atomic(self, path: str, content: bytes):
        """Helper to write file atomically (tmp -> fsync -> rename)."""
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)

    def shatter_file(self, file_path: str, output_dir: str = None, callback=None, delete_original: bool = False):
        """
        Dosyayı parçalar, şifreler ve manifest oluşturur.
        Authentication: Manifest içindeki chunk key'ler MasterKey ile Wrap edilir.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        if output_dir is None:
            output_dir = os.path.dirname(file_path)
            
        # Create Output Directory
        target_folder_name = filename + "_sharded"
        target_folder_path = os.path.join(output_dir, target_folder_name)
        os.makedirs(target_folder_path, exist_ok=True)
            
        # v3.0: Generate Master Key upfront for Key Wrapping
        manifest_salt = os.urandom(16)
        master_key = self.crypto.derive_master_key(manifest_salt)
        
        chunk_size = self._calculate_chunk_size(file_size)
            
        manifest_data = {
            "version": 3.0, # Version bumped
            "original_filename": filename,
            "original_size": file_size,
            "chunk_size": chunk_size,
            "chunks": []
        }
        
        chunk_index = 0
        total_chunks = (file_size // chunk_size) + (1 if file_size % chunk_size > 0 else 0)
        
        start_time = time.time()
        processed_bytes = 0
        
        with open(file_path, "rb") as f:
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                # Update processed bytes
                processed_bytes += len(chunk_data)
                
                # 1. Generate Unique Key
                chunk_key = self.crypto.generate_chunk_key()
                
                # 2. Hash (Plaintext)
                chunk_hash = self.crypto.calculate_hash(chunk_data)
                
                # 3. Encrypt Chunk (With context)
                nonce, ciphertext = self.crypto.encrypt_chunk(chunk_data, chunk_key, chunk_index)
                
                # 4. Write Encrypted Chunk Atomically
                chunk_uuid = uuid.uuid4().hex
                chunk_filename = f"{chunk_uuid}{self.ENCRYPTED_CHUNK_EXT}"
                chunk_path = os.path.join(target_folder_path, chunk_filename)
                
                self._write_atomic(chunk_path, nonce + ciphertext)
                
                # 5. Key Wrapping (Protect Chunk Key with Master Key + Context Binding)
                # Context is the UUID of the chunk. This prevents 'cut-and-paste' attacks.
                wrapped_key = self.crypto.wrap_key(master_key, chunk_key, context=chunk_uuid)
                
                manifest_data["chunks"].append({
                    "index": chunk_index,
                    "id": chunk_uuid,
                    "filename": chunk_filename,
                    "key": base64.b64encode(wrapped_key).decode('utf-8'),
                    "hash": chunk_hash
                })
                
                # Memory Cleanup for key
                del chunk_key
                
                chunk_index += 1
                if callback:
                    elapsed = time.time() - start_time
                    speed_mb = (processed_bytes / (1024 * 1024)) / (elapsed if elapsed > 0 else 1)
                    progress = (chunk_index / total_chunks) * 100
                    callback(progress, f"Parçalanıyor: {chunk_index}/{total_chunks} ({speed_mb:.1f} MB/s)")
                    
        # 6. Save Manifest (Encrypted with Master Key)
        self._save_manifest(manifest_data, target_folder_path, filename, master_key, manifest_salt)
        
        # Cleanup Master Key
        del master_key
        
        if delete_original:
            if callback: callback(1.0, "Orijinal dosya güvenli siliniyor...")
            self._secure_delete(file_path)
        
        return target_folder_path

    def _save_manifest(self, manifest_dict: Dict, output_dir: str, original_filename: str, master_key: bytes, salt: bytes):
        """Manifest verisini şifreleyip kaydeder."""
        json_bytes = json.dumps(manifest_dict).encode('utf-8')
        
        # Encrypt the JSON body as usual
        nonce, ciphertext = self.crypto.encrypt_chunk(json_bytes, master_key, 0) # Index 0 for manifest context
        
        manifest_filename = f"{original_filename}{self.MANIFEST_EXT}"
        manifest_path = os.path.join(output_dir, manifest_filename)
        
        # Write Main Manifest
        with open(manifest_path, "wb") as mf:
            # Structure: [Salt 16][Nonce 12][Ciphertext]
            mf.write(salt + nonce + ciphertext)
            mf.flush()
            os.fsync(mf.fileno())
            
        # Backup
        backup_path = manifest_path + ".bak"
        shutil.copy2(manifest_path, backup_path)

    def scan_directory_for_manifests(self, directory_path: str) -> List[str]:
        """
        Verilen klasörü (ve alt klasörleri) tarayarak .shatter_manifest dosyalarını bulur.
        """
        manifests = []
        if not os.path.exists(directory_path):
            return manifests
            
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith(self.MANIFEST_EXT):
                    manifests.append(os.path.join(root, file))
        
        return manifests

    def _read_and_decrypt_chunk(self, chunk_info: Dict, base_dir: str, master_key: bytes):
        """Helper method for parallel processing."""
        chunk_filename = chunk_info["filename"]
        chunk_path = os.path.join(base_dir, chunk_filename)
        
        if not os.path.exists(chunk_path):
            raise FileNotFoundError(f"Parça eksik: {chunk_filename}")
        
        # v3.0: Unwrap Key (Context = Chunk UUID)
        # We try to get 'id' from manifest. If not present (v2.5 legacy), handle gracefully or fail.
        # Since v3.0 is a breaking change, we enforce 'id'.
        chunk_uuid = chunk_info.get("id")
        if not chunk_uuid:
             raise ValueError(f"Manifest v3.0 uyumsuz (Chunk ID eksik). Index: {chunk_info['index']}")
             
        wrapped_key = base64.b64decode(chunk_info["key"])
        try:
            chunk_key = self.crypto.unwrap_key(master_key, wrapped_key, context=chunk_uuid)
        except Exception as e:
            raise ValueError(f"Anahtar açma hatası (Key Wrap Fail / Context Mismatch) - Index {chunk_info['index']}") from e

        expected_hash = chunk_info["hash"]
        
        # Read Encrypted Chunk
        with open(chunk_path, "rb") as cf:
            file_content = cf.read()
            
        # Extract Nonce (First 12 bytes)
        nonce = file_content[:12]
        ciphertext = file_content[12:]
        
        # Decrypt (With Context)
        plaintext = self.crypto.decrypt_chunk(nonce, ciphertext, chunk_key, chunk_info['index'])
        
        # Verify Hash (Integrity Check)
        current_hash = self.crypto.calculate_hash(plaintext)
        if current_hash != expected_hash:
            raise ValueError(f"Bütünlük Hatası! Parça {chunk_info['index']} bozulmuş (Hash Mismatch).")
            
        return plaintext

    def reassemble_file(self, manifest_path: str, output_dir: str = None, callback=None, delete_source: bool = True):
        """
        Manifest dosyasını okur, şifreli parçaları bulur, paralel olarak çözer ve birleştirir.
        v3.0: Key Unwrapping ve Context-Aware Decryption eklendi.
        """
        if not os.path.exists(manifest_path):
            raise FileNotFoundError("Manifest bulunamadı.")
            
        # 1. Load & Decrypt Manifest (Returns Data AND MasterKey now)
        manifest_data, master_key = self._load_manifest(manifest_path)
        
        base_dir = os.path.dirname(manifest_path)
        
        # determine Output Directory (Safe Check)
        if output_dir is None:
            output_dir = os.path.dirname(base_dir)
        else:
            if delete_source:
                abs_output = os.path.abspath(output_dir)
                abs_base = os.path.abspath(base_dir)
                if abs_output == abs_base or abs_output.startswith(abs_base + os.sep):
                    print(f"UYARI: Hedef klasör ({output_dir}) silinecek klasörün içinde! Üst dizine geçiliyor.")
                    output_dir = os.path.dirname(abs_base)

        original_filename = manifest_data["original_filename"]
        target_path = os.path.join(output_dir, original_filename)
        
        chunks = manifest_data["chunks"]
        total_chunks = len(chunks)
        
        # Sort chunks by index
        chunks.sort(key=lambda x: x["index"])
        
        # 2. Parallel Decryption & Sequential Write
        try:
            # Atomic Write for Reassembled File not strictly necessary but good practice
            # Writing directly to target for now, but ensure cleanup on fail.
            with open(target_path, "wb") as tf:
                max_workers = min(32, (os.cpu_count() or 1) + 4)
                
                processed_bytes = 0
                start_time = time.time()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Pass master_key to the helper via lambda
                    future_results = executor.map(lambda c: self._read_and_decrypt_chunk(c, base_dir, master_key), chunks)
                    
                    for i, plaintext in enumerate(future_results):
                        tf.write(plaintext)
                        
                        processed_bytes += len(plaintext)
                        
                        if callback:
                            elapsed = time.time() - start_time
                            speed_mb = (processed_bytes / (1024 * 1024)) / (elapsed if elapsed > 0 else 1)
                            progress = ((i + 1) / total_chunks) * 100
                            callback(progress, f"Birleştiriliyor: {i+1}/{total_chunks} ({speed_mb:.1f} MB/s)")
                            
        except Exception as e:
            if os.path.exists(target_path): os.remove(target_path)
            raise e
        finally:
            # Memory Cleanup
            del master_key
        
        # 3. Cleanup Source (If requested)
        if delete_source:
            try:
                for chunk in chunks:
                    cp = os.path.join(base_dir, chunk["filename"])
                    if os.path.exists(cp): os.remove(cp)
                
                if os.path.exists(manifest_path):
                    os.remove(manifest_path)
                    
                backup_path = manifest_path + ".bak"
                if os.path.exists(backup_path): os.remove(backup_path)
                    
                if base_dir.endswith("_sharded"):
                    shutil.rmtree(base_dir, ignore_errors=True)
            except Exception as e:
                print(f"Cleanup Warning: {e}")
                    
        return target_path

    def _load_manifest(self, manifest_path: str) -> tuple[Dict, bytes]:
        """
        Şifreli manifest dosyasını okur ve (JSON dict, MasterKey) döner.
        v3.0: Master Key'i de dönüyor çünkü Key Unwrap için lazım.
        """
        with open(manifest_path, "rb") as mf:
            data = mf.read()
            
        if len(data) < 16 + 12:
            raise ValueError("Manifest dosyası bozuk (çok kısa).")
            
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        
        # Derive Master Key (Argon2id takes time, do it once)
        master_key = self.crypto.derive_master_key(salt)
        
        try:
            # Decrypt Manifest JSON (Context Index 0)
            json_bytes = self.crypto.decrypt_chunk(nonce, ciphertext, master_key, 0)
            return json.loads(json_bytes.decode('utf-8')), master_key
        except Exception as e:
            # Ensure key cleanup on error if possible, though local scope handles it mostly.
            del master_key 
            raise ValueError("Manifest şifresi çözülemedi. Parola yanlış veya dosya bozuk.") from e
