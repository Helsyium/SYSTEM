import os
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes, constant_time
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

class SecurityManager:
    """
    Güvenlik ve anahtar yönetimi işlemlerini yürüten sınıf.
    Scrypt ile anahtar türetme ve HKDF ile alt anahtar oluşturma işlemlerini yapar.
    """

    def __init__(self):
        # KDF yapılandırması derive_master_key içinde yapılacak
        pass

    def derive_master_key(self, password: str, salt: bytes) -> bytes:
        """
        Kullanıcı parolasından ana anahtarı (Master Key) türetir.
        
        Args:
            password: Kullanıcı parolası
            salt: Rastgele üretilmiş salt (en az 16 byte)
            
        Returns:
            32 byte (256-bit) ham anahtar
        """
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**16, # 64K iterasyon (Memory cost)
            r=8,     # Block size
            p=1,     # Parallelization
        )
        return kdf.derive(password.encode('utf-8'))

    def derive_file_key(self, master_key: bytes, file_salt: bytes) -> bytes:
        """
        Ana anahtardan dosya bazlı benzersiz anahtar türetir.
        Bu sayede her dosya farklı bir anahtarla şifrelenir ve Nonce reuse riski ortadan kalkar.
        
        Args:
            master_key: Ana anahtar
            file_salt: Dosyaya özel rastgele salt
            
        Returns:
            32 byte dosya anahtarı
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=file_salt,
            info=b'file-encryption-key'
        )
        return hkdf.derive(master_key)

    @staticmethod
    def generate_salt(length=16) -> bytes:
        """Güvenli rastgele salt üretir."""
        return os.urandom(length)

    @staticmethod
    def verify_password(stored_hash: bytes, password: str) -> bool:
        """
        Saklanan hash ile parolanın uyuşup uyuşmadığını kontrol eder.
        (Uygulama giriş güvenliği için kullanılabilir)
        Argon2 bu formatı kendi içinde barındırır ($argon2id$...)
        """
        # Not: Bu fonksiyon uygulama girişi için parola hash'i saklanacaksa kullanılır.
        # Dosya şifrelemede her seferinde anahtar türetilir.
        # Bu basitlik için şimdilik implemente etmiyoruz veya ayrı bir kütüphane çağrısı gerekir.
        pass
