import os
import shutil
import random
from typing import List, Callable
from .crypto_manager import CryptoManager
from ..utils.config import ENCRYPTED_EXT

class FileManager:
    """
    Dosya sistemi işlemlerini, güvenli silme ve klasör gezinme mantığını yönetir.
    """
    MANIFEST_FILENAME = ".vault_manifest"
    
    def __init__(self, crypto_manager: CryptoManager):
        self.crypto = crypto_manager

    def secure_delete(self, path: str, passes: int = 1):
        """
        Dosyayı güvenli bir şekilde siler (Wipe/Shred).
        Üzerine rastgele veri yazar ve sonra siler.
        SSD disklerde TRIM komutu nedeniyle %100 garanti vermez ama OS düzeyinde en iyisidir.
        
        Args:
            path: Silinecek dosya yolu
            passes: Kaç kez üzerine yazılacağı (Hız için varsayılan 1)
        """
        if not os.path.exists(path):
            return

        length = os.path.getsize(path)
        
        with open(path, "wb") as f:
            for _ in range(passes):
                f.seek(0)
                # Büyük dosyalar için chunk chunk yaz
                written = 0
                while written < length:
                    chunk_size = min(64 * 1024, length - written)
                    f.write(os.urandom(chunk_size))
                    written += chunk_size
                f.flush()
                os.fsync(f.fileno()) # Veriyi diske zorla
                
        os.remove(path)

    def process_folder(self, folder_path: str, mode: str = 'encrypt', callback=None):
        """
        Klasörü gezer ve tüm içeriği şifreler veya çözer.
        topdown=False kullanarak en derinden yukarıya doğru işlem yapar.
        
        Args:
            folder_path: İşlenecek klasör
            mode: 'encrypt' veya 'decrypt'
            callback: İlerleme bildirimi fonksiyonu (opsiyonel) -> callback(current_file)
        """
        if mode not in ['encrypt', 'decrypt']:
            raise ValueError("Invalid mode")

        manifest_path = os.path.join(folder_path, self.MANIFEST_FILENAME)

        if mode == 'encrypt':
            # Çifte şifreleme kontrolü
            if os.path.exists(manifest_path):
                # Dosya var, içi doğru mu? (Varsa önce load etmeye çalış)
                with open(manifest_path, "rb") as f:
                    data = f.read()
                    
                is_valid = self.crypto.load_and_verify_manifest(data)
                
                if is_valid:
                    raise ValueError("Bu klasör zaten bu şifreyle şifrelenmiş!")
                else:
                    raise ValueError("Bu klasörde zaten bir kilit dosyası (.vault_manifest) var. Şifreli olabilir.")
            
            # Yeni Manifest oluştur ve yaz
            manifest_content = self.crypto.initialize_new_vault()
            with open(manifest_path, "wb") as f:
                f.write(manifest_content)
                f.flush()
                os.fsync(f.fileno()) # Diske yazılmasını garanti et
            
            # Manifest Yedekleme (Backup) - Production Readiness
            # Ana dosya bozulursa kurtarmak için
            manifest_backup_path = manifest_path + ".bak"
            shutil.copy2(manifest_path, manifest_backup_path)
            
        else: # decrypt
            if os.path.exists(manifest_path):
                with open(manifest_path, "rb") as f:
                    data = f.read()
                    
                try:
                    self.crypto.load_and_verify_manifest(data)
                except Exception as e:
                    raise ValueError(f"Hatalı Şifre! Manifest doğrulanamadı. Detay: {str(e)}")
            else:
                # Manifest yoksa işlem yapamayız çünkü Master Key yok!
                raise ValueError("Manifest dosyası (.vault_manifest) bulunamadı! Şifre çözülemez.")

        # Topdown=False önemli: Önce çocukları işle, sonra ebeveyn klasör adını değiştir.
        for root, dirs, files in os.walk(folder_path, topdown=False):
            # Manifest dosyasını listeden çıkar (işlem görmesin)
            if self.MANIFEST_FILENAME in files:
                files.remove(self.MANIFEST_FILENAME)
            # 1. Dosyaları işle
            for name in files:
                file_path = os.path.join(root, name)
                
                # MacOS sistem dosyalarını atla (.DS_Store vb)
                if name.startswith('.') or name == '.DS_Store':
                    continue

                if mode == 'encrypt':
                    # Eğer zaten şifreliyse (.agv) atla
                    if name.endswith(ENCRYPTED_EXT):
                        continue
                        
                    self._encrypt_single_file(file_path)
                    
                else: # decrypt
                    # Sadece .agv dosyalarını işle
                    if not name.endswith(ENCRYPTED_EXT):
                        continue
                    
                    self._decrypt_single_file(file_path)

                if callback:
                    callback(name)

            # 2. Klasör isimlerini işle (Root klasör hariç, onu kullanıcı seçtiği için sabit kalsın mı?
            # Kullanıcının seçtiği klasörün ADI değişirse kullanıcı onu bulamayabilir.
            # Genelde kök klasör adı sabit kalır, içeriği değişir.
            # Ancak `root` değişkeni şu anki gezilen klasör.
            # Eğer `root` == `folder_path` ise ismini değiştirme opsiyonu ekleyebiliriz.
            # Şimdilik içeriği şifreliyoruz, root klasör adını da şifrelemek karışıklık yaratabilir.
            # Ama alt klasörlerin adı mutlaka şifrelenmeli.
            
            if root == folder_path:
                continue

            # Alt Klasör adını değiştir
            # os.walk döngüsü sürerken klasör adını değiştirmek sorun yaratmaz çünkü 
            # topdown=False ile zaten o klasörün işi bitmiştir, bir üstteyizdir.
             # Hata: topdown=False da `root`, `dirs` listesindekilerin parentıdır.
            # Hayır, `root` şu anki klasördür.
            # `dirs` ise `root`un içindeki klasörlerdir.
            # Biz `root` içindekileri işledik. Şimdi `root`un kendi ismini değiştirmeliyiz ama
            # os.walk yapısında `root` değişkeni stringdir, onu rename edemeyiz (parent lazım).
            # Doğrusu: os.walk ile `dirs` listesindeki klasörleri rename etmek.
            # AMA `topdown=False` olunca `dirs` zaten işlenmiş midir?
            # EVET. `topdown=False` demek: Önce alt klasörleri ziyaret et (yield et), sonra parent'ı.
            # Yani biz şu an `root`tayız ve buradaki işimiz bitti.
            # Ama `root` dizinini rename edersek, bir sonraki iterasyonda (parent'a çıkınca)
            # os.walk şaşırır mı? Hayır, çünkü os.walk listeyi önceden oluşturur mu?
            # Python os.walk `topdown=False` mantığında, directoryleri yield ettikten sonra parenta geçer.
            # Biz `root` klasörünün içindeyiz. Bu klasörün ismini değiştirmek için
            # Parent klasörü bilmemiz lazım (`os.path.dirname(root)`).
            # Ve `root` klasörünü rename edebiliriz.
            
            encryption_marker = ".enc" # Klasör şifreli mi anlamak için basit marker (opsiyonel)
            # Dosya uzantısı gibi değil ama klasör isminin şifreli olup olmadığını anlamak zor.
            # O yüzden klasör isimlerini de `[Base64]` formatına çeviriyoruz.
            # Şifreli isimler URLSAFE Base64 karakterleri içerir. Anlamsız görünür.
            
            parent_dir = os.path.dirname(root)
            dir_name = os.path.basename(root)
            
            if mode == 'encrypt':
                # Klasör adını şifrele
                encrypted_name = self.crypto.encrypt_filename(dir_name)
                # İsim çakışmasını önlemek için
                new_path = os.path.join(parent_dir, encrypted_name)
                os.rename(root, new_path)
            
            else: # decrypt
                # Klasör adını çöz
                # Şifreli isim mi? Deneyelim.
                decrypted_name = self.crypto.decrypt_filename(dir_name)
                if decrypted_name:
                    new_path = os.path.join(parent_dir, decrypted_name)
                    os.rename(root, new_path)
        
        if mode == 'decrypt' and os.path.exists(manifest_path):
            # Manifest'i sadece başarılı çözme sonunda silmemiz lazım
            # Ama dosya bazlı çalıştığımız için tek tek siliyoruz.
            if self.crypto.master_key:
                self.secure_delete(manifest_path)
                # Varsa yedeği de sil
                manifest_backup_path = manifest_path + ".bak"
                if os.path.exists(manifest_backup_path):
                    self.secure_delete(manifest_backup_path)



    def _encrypt_single_file(self, file_path: str):
        """Yardımcı: Tek dosyayı şifrele (Atomik), eskisini sil"""
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        
        # Path Length Check (Yaklaşık)
        # Şifreli isim Base64 ile uzayacak (%33 artış + overhead).
        # Güvenli limit: OS MAX_PATH (Genelde 260) - Güvenlik Payı.
        # Eğer çok uzunsa hata ver.
        encrypted_name_preview = self.crypto.encrypt_filename(base_name)
        potential_path_len = len(dir_name) + len(encrypted_name_preview) + len(ENCRYPTED_EXT) + 1
        
        if potential_path_len > 250: # Windows limiti 260, 250 güvenlik sınırı.
             raise ValueError(f"Dosya yolu çok uzun! Şifrelenmiş isim limiti aşıyor: {file_path}")

        # 1. İçeriği şifrele: filename.ext -> filename.ext.agv.tmp (geçici)
        temp_encrypted_path = file_path + ENCRYPTED_EXT + ".tmp"
        
        try:
            self.crypto.encrypt_file(file_path, temp_encrypted_path)
            
            # 2. Rename .tmp -> .agv (Atomik benzeri)
            # Önce hedef ismi belirle (Geçici encrypted name)
            # İsim şifreleme son aşamada olduğu için burada dosya adı henüz şifresiz kalıyor
            # Ancak biz içeriği şifreledik.
            # Akış:
            # A. İçerik Şifrele: foo.txt -> foo.txt.agv.tmp -> foo.txt.agv
            # B. Orijinal Sil: foo.txt
            # C. İsim Şifrele: foo.txt.agv -> ENCRYPTED_NAME.agv
            
            intermediate_path = file_path + ENCRYPTED_EXT
            os.replace(temp_encrypted_path, intermediate_path)
            
            # 3. Orijinali güvenli sil
            self.secure_delete(file_path)
            
            # 4. Dosya ismini şifrele ve rename et
            # encrypted_name_preview zaten yukarıda hesaplandı ama nonce değişir. Tekrar yapalım.
            encrypted_filename = self.crypto.encrypt_filename(base_name) + ENCRYPTED_EXT
            final_path = os.path.join(dir_name, encrypted_filename)
            
            os.rename(intermediate_path, final_path)
            
        except Exception as e:
            # Hata varsa temizlik yap
            if os.path.exists(temp_encrypted_path):
                os.remove(temp_encrypted_path)
            raise e

    def _decrypt_single_file(self, file_path: str):
        """Yardımcı: Tek dosyayı çöz (Atomik)"""
        # file_path şuan EncryptedName.agv
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        
        # Uzantıyı at (.agv)
        encrypted_name_only = os.path.splitext(base_name)[0]
        
        # 1. İsmi çöz
        decrypted_filename = self.crypto.decrypt_filename(encrypted_name_only)
        
        if not decrypted_filename:
            # Şifreli isim değilse
             decrypted_filename = "decrypted_" + encrypted_name_only
        
        # 2. İçeriği çöz: Hedef -> Hedef.tmp
        final_output_path = os.path.join(dir_name, decrypted_filename)
        temp_output_path = final_output_path + ".tmp"
        
        try:
            self.crypto.decrypt_file(file_path, temp_output_path)
            
            # Başarılı ise atomik rename
            os.replace(temp_output_path, final_output_path)
            
            # Şifreli dosyayı sil
            os.remove(file_path)
        except Exception as e:
            print(f"Hata: {file_path} çözülemedi. {e}")
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)

