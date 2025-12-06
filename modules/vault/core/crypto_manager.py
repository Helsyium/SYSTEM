import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import base64
from .security import SecurityManager
from ..utils.config import GLOBAL_VAULT_SALT, ENCRYPTED_EXT

class CryptoManager:
    """
    Dosya şifreleme ve deşifreleme işlemlerini yöneten sınıf.
    Büyük dosyalar için chunk-based (parçalı) şifreleme kullanır.
    
    V3 Update:
    - Global Salt kaldırıldı, Dinamik Vault Salt eklendi.
    - Chunk Integrity için Associated Data (AD) kullanımı.
    - Master Key cache mekanizması.
    """
    
    CHUNK_SIZE = 64 * 1024  # 64 KB okuma boyutu
    NONCE_SIZE = 12
    TAG_SIZE = 16
    SALT_SIZE = 16 # Vault Salt Size
    
    # Manifest Yapısı: [MAGIC(23)] + [SALT(16)] + [NONCE(12)] + [CIPHERTEXT]
    MANIFEST_MAGIC = b"ANTIGRAVITY_VAULT_OK_v2" 
    
    # Chunk Overhead: Nonce + Tag
    ENCRYPTED_CHUNK_OVERHEAD = NONCE_SIZE + TAG_SIZE

    def __init__(self, password: str):
        self.password = password
        self.security = SecurityManager()
        self.master_key = None
        self.vault_salt = None

    def initialize_new_vault(self) -> bytes:
        """
        Yeni bir vault oluşturur (Manifest içeriği üretir).
        Random salt üretir ve master key türetir.
        Return: Manifest dosya içeriği (bytes)
        """
        try:
            self.vault_salt = self.security.generate_salt(self.SALT_SIZE)
            self.master_key = self.security.derive_master_key(self.password, self.vault_salt)
            
            # Manifest'i şifrele (Kendi Master Key'i ile)
            # Manifest Key türet
            manifest_key = self.security.derive_file_key(self.master_key, b'MANIFEST_KEY_SALT')
            cipher = ChaCha20Poly1305(manifest_key)
            
            nonce = os.urandom(self.NONCE_SIZE)
            # İçerik olarak Magic String şifreliyoruz.
            ciphertext = cipher.encrypt(nonce, self.MANIFEST_MAGIC, None)
            
            # Format: [SALT(16)] + [NONCE(12)] + [CIPHERTEXT (Magic)]
            return self.vault_salt + nonce + ciphertext
        except Exception as e:
            raise e

    def load_and_verify_manifest(self, manifest_data: bytes) -> bool:
        """
        Manifest verisini yükler ve doğrular.
        Başarılıysa self.master_key ve self.vault_salt set edilir.
        """
    def load_and_verify_manifest(self, manifest_data: bytes) -> bool:
        """
        Manifest verisini yükler ve doğrular.
        Başarılıysa self.master_key ve self.vault_salt set edilir.
        Hata durumunda Exception fırlatır.
        """
        if len(manifest_data) < self.SALT_SIZE + self.NONCE_SIZE + self.TAG_SIZE:
             raise ValueError("Manifest dosyası çok kısa (Bozuk veya eksik).")
            
        # Parse
        salt = manifest_data[:self.SALT_SIZE]
        nonce = manifest_data[self.SALT_SIZE : self.SALT_SIZE + self.NONCE_SIZE]
        ciphertext = manifest_data[self.SALT_SIZE + self.NONCE_SIZE:]
        
        # Key Derivation
        derived_master_key = self.security.derive_master_key(self.password, salt)
        
        manifest_key = self.security.derive_file_key(derived_master_key, b'MANIFEST_KEY_SALT')
        
        try:
            cipher = ChaCha20Poly1305(manifest_key)
            decrypted_magic = cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            # Şifre yanlışsa veya dosya bozuksa burası patlar
            raise ValueError("Kriptografik doğrulama başarısız (Yanlış Şifre?)") from e
        
        if decrypted_magic == self.MANIFEST_MAGIC:
            self.vault_salt = salt
            self.master_key = derived_master_key
            return True
            
        raise ValueError(f"Manifest Magic uyuşmuyor: {decrypted_magic}")
            
    def clear_memory(self):
        """
        Hassas verileri (parola, anahtarlar) bellekten silmeyi dener.
        """
        self.password = None
        self.master_key = None
        self.vault_salt = None

    def check_state(self):
        if not self.master_key:
            raise ValueError("Vault is not initialized or unlocked (Master Key missing). check manifest first.")

    def encrypt_file(self, input_path: str, output_path: str):
        """
        Dosyayı şifreler. Associated Data olarak Chunk Index kullanır.
        """
        self.check_state()
        
        # Her dosya için salt
        file_salt = self.security.generate_salt(self.SALT_SIZE)
        file_key = self.security.derive_file_key(self.master_key, file_salt)
        cipher = ChaCha20Poly1305(file_key)

        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            # Header: FileSalt
            fout.write(file_salt)
            
            chunk_index = 0
            while True:
                chunk = fin.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                
                nonce = os.urandom(self.NONCE_SIZE)
                
                # AD: Chunk Index (Little Endian 64-bit unsigned)
                ad = struct.pack("<Q", chunk_index)
                
                ciphertext = cipher.encrypt(nonce, chunk, ad)
                
                fout.write(nonce)
                fout.write(ciphertext)
                
                chunk_index += 1

    def decrypt_file(self, input_path: str, output_path: str):
        """
        Dosyayı çözer. Associated Data (Chunk Index) doğrular.
        """
        self.check_state()

        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            file_salt = fin.read(self.SALT_SIZE)
            if len(file_salt) != self.SALT_SIZE:
                raise ValueError("Bozuk dosya.")
            
            file_key = self.security.derive_file_key(self.master_key, file_salt)
            cipher = ChaCha20Poly1305(file_key)
            
            chunk_index = 0
            while True:
                nonce = fin.read(self.NONCE_SIZE)
                if not nonce:
                    break
                    
                # Encrypted Chunk Size = Data + Tag
                # Data size değişken olabilir (son chunk).
                # Okurken ne kadar okuyacağız?
                # Chunked formatta yazarken boyut bilgisi yazmadık, 
                # bu yüzden stream decrypt zordur çünkü tag nerede bitiyor bilemeyiz (eğer chunk size değişken ise).
                # V2 Düzeltme: CHUNK_SIZE sabit olduğunda sorun yok (son parça hariç).
                # Ama son parçanın boyutunu bilmek için dosya sonuna bakabiliriz.
                
                # Mevcut okuma pozisyonu
                pos = fin.tell()
                # Kalan boyut
                fin.seek(0, 2) # EOF
                file_size = fin.tell()
                fin.seek(pos) # Geri dön
                
                remaining = file_size - pos
                
                # Normal bir chunk (NONCE hariç) = CHUNK_SIZE + TAG_SIZE
                expected_full_chunk_data = self.CHUNK_SIZE + self.TAG_SIZE
                
                # Okuyacağımız miktar
                read_size = min(expected_full_chunk_data, remaining)
                
                ciphertext_with_tag = fin.read(read_size)
                
                if not ciphertext_with_tag:
                    break

                ad = struct.pack("<Q", chunk_index)
                
                try:
                    decrypted_chunk = cipher.decrypt(nonce, ciphertext_with_tag, ad)
                    fout.write(decrypted_chunk)
                except Exception as e:
                    raise ValueError(f"Chunk {chunk_index} integrity check failed! File corrupted or tampering detected.") from e
                
                chunk_index += 1

    def encrypt_filename(self, filename: str) -> str:
        self.check_state()
        # İsim anahtarı statik salt ile ama master_key dinamik (vault'a özel)
        name_key = self.security.derive_file_key(self.master_key, b'FILENAME_ENCRYPTION_SALT')
        cipher = ChaCha20Poly1305(name_key)
        
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = cipher.encrypt(nonce, filename.encode('utf-8'), None)
        
        return base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt_filename(self, encrypted_name: str) -> str:
        self.check_state()
        try:
            data = base64.urlsafe_b64decode(encrypted_name)
            nonce = data[:self.NONCE_SIZE]
            ciphertext = data[self.NONCE_SIZE:]
            
            name_key = self.security.derive_file_key(self.master_key, b'FILENAME_ENCRYPTION_SALT')
            cipher = ChaCha20Poly1305(name_key)
            
            return cipher.decrypt(nonce, ciphertext, None).decode('utf-8')
        except Exception:
            return None
