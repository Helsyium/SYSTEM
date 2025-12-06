import os
import secrets
import hashlib
import struct
import hmac
import argon2
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class ShatterCrypto:
    """
    SHATTER Modülü için Kriptografi Motoru (v3.0 Hardened).
    
    Yenilikler:
    - KDF: Argon2id (Low-level API)
    - Nonce: Deterministic (HMAC-SHA256)
    - Key Wrapping: AEAD protected with Context Binding (UUID)
    - Randomness: secrets.token_bytes (Explicit CSPRNG)
    """
    
    KEY_SIZE = 32
    NONCE_SIZE = 12
    SALT_SIZE = 16
    
    def __init__(self, password: str = None):
        self.password = password
        
    def generate_chunk_key(self) -> bytes:
        """Her parça için 256-bit tamamen rastgele (unique) anahtar üretir."""
        return secrets.token_bytes(self.KEY_SIZE)
    
    def derive_deterministic_nonce(self, key: bytes, context: bytes = b'chunk') -> bytes:
        """
        Verilen anahtar ve bağlamdan deterministik olarak 12-byte nonce türetir.
        Yöntem: HMAC-SHA256(Key, Context)[:12]
        """
        h = hmac.new(key, context, hashlib.sha256)
        return h.digest()[:self.NONCE_SIZE] # TRUNCATION: 32 -> 12 bytes

    def encrypt_chunk(self, chunk_data: bytes, key: bytes, chunk_index: int = 0) -> tuple[bytes, bytes]:
        """
        Verilen parçayı şifreler.
        """
        context = struct.pack("<Q", chunk_index) 
        nonce = self.derive_deterministic_nonce(key, context)
        
        cipher = ChaCha20Poly1305(key)
        
        # AD: Index context ensures chunk order integrity
        ciphertext = cipher.encrypt(nonce, chunk_data, context)
        
        return nonce, ciphertext

    def decrypt_chunk(self, nonce: bytes, ciphertext: bytes, key: bytes, chunk_index: int = 0) -> bytes:
        """Şifreli parçayı çözer."""
        cipher = ChaCha20Poly1305(key)
        context = struct.pack("<Q", chunk_index)
        try:
            plaintext = cipher.decrypt(nonce, ciphertext, context)
            return plaintext
        except Exception as e:
            raise ValueError(f"Parça şifresi çözülemedi (Index: {chunk_index}). Bütünlük hatası.") from e

    def calculate_hash(self, data: bytes) -> str:
        """Verinin SHA-256 özetini (hex string) hesaplar."""
        sha256 = hashlib.sha256()
        sha256.update(data)
        return sha256.hexdigest()

    def derive_master_key(self, salt: bytes) -> bytes:
        """
        Kullanıcı parolası ve Salt'tan Master Key türetir.
        v3.0: Argon2id kullanımı (argon2-cffi low_level API).
        Parametreler:
        - memory_cost: 64 MB (65536 KiB)
        - time_cost: 2 pass
        - parallelism: 2 threads
        - type: Argon2id
        """
        if not self.password:
            raise ValueError("Parola belirlenmemiş.")
            
        return argon2.low_level.hash_secret_raw(
            secret=self.password.encode(),
            salt=salt,
            time_cost=2,
            memory_cost=65536,
            parallelism=2,
            hash_len=32,
            type=argon2.low_level.Type.ID
        )

    def wrap_key(self, master_key: bytes, key_to_wrap: bytes, context: str = "key_wrap") -> bytes:
        """
        Bir anahtarı (ChunkKey) MasterKey ile şifreler (Wrap).
        Bu sayede Manifest çalınsa bile, MasterKey olmadan içindeki anahtarlar görülemez.
        """
        # Wrapping Key türet (Master Key'i direkt kullanmak yerine subkey kullanmak daha iyidir)
        # Ancak basitlik ve performans için burada MasterKey üzerinden ChaCha20 ile şifreliyoruz.
        # Her wrap işlemi için random nonce üretiyoruz.
        
        # Context'i AD olarak kullan
        ad = context.encode('utf-8')
        
        nonce = os.urandom(self.NONCE_SIZE)
        cipher = ChaCha20Poly1305(master_key)
        ciphertext = cipher.encrypt(nonce, key_to_wrap, ad)
        
        # Return format: [Nonce 12][Ciphertext 32 + 16(tag) = 48] = 60 bytes total
        return nonce + ciphertext

    def unwrap_key(self, master_key: bytes, wrapped_data: bytes, context: str = "key_wrap") -> bytes:
        """Sarmalanmış anahtarı açar."""
        if len(wrapped_data) < self.NONCE_SIZE:
             raise ValueError("Invalid wrapped key format")
             
        nonce = wrapped_data[:self.NONCE_SIZE]
        ciphertext = wrapped_data[self.NONCE_SIZE:]
        ad = context.encode('utf-8')
        
        cipher = ChaCha20Poly1305(master_key)
        try:
            return cipher.decrypt(nonce, ciphertext, ad)
        except Exception as e:
            raise ValueError("Key unwrap failed") from e
