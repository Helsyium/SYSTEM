# SYSTEM HUB - Secure Digital Vault & File Shredder

**SYSTEM HUB**, kişisel veri güvenliği için geliştirilmiş modüler bir güvenlik platformtur. **Askeri standartlarda şifreleme** ve **kriptografik dosya imhası** (sharding) teknolojilerini kullanıcı dostu modern bir arayüzle sunar.

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Security](https://img.shields.io/badge/Security-Hardened%20v3.5-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Modüller

Proje, tek bir çatı altında çalışan iki güçlü modülden oluşur:

### 1. 🛡️ VAULT (Folder Locker)
Klasörlerinizi saniyeler içinde şifreleyerek görünmez hale getirir.
- **AES-256-GCM** şifreleme.
- **Scrypt** KDF (Tuş türetme) ile kaba kuvvet koruması.
- Dosya ve klasör isimlerini şifreleyerek tam gizlilik sağlar.

### 2. 🧩 SHATTER v3.5 (File Sharding Engine)
Dosyalarınızı şifreleyip binlerce anlamsız parçaya böler.
- **ChaCha20-Poly1305** (AEAD) şifreleme.
- **Argon2id** (64MB, 2-Pass) bellek dirençli KDF.
- **Shard-Level Encryption:** Her parça 32-byte *benzersiz* anahtarla şifrelenir.
- **Deterministic Nonce Strategy:** `HMAC-SHA256` tabanlı nonce üretimi (%0 Çakışma).
- **Context-Bound Key Wrapping:** Chunk anahtarları manifest dosyasında çıplak saklanmaz; ana anahtar ve Chunk UUID ile mühürlenir ("Cut-and-Paste" saldırılarına karşı korumalı).
- **Atomic I/O:** Elektrik kesintisinde veri kaybı yaşanmaz.

---

## 🛠️ Kurulum (Installation)

### Gereksinimler
- Python 3.10+
- `pip`

### Adımlar

1. **Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/username/system-hub.git
   cd system-hub
   ```

2. **Bağımlılıkları Yükleyin:**
   ```bash
   # Sanal ortam oluşturma (Önerilir)
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows

   # Paketleri yükleme
   pip install -r requirements.txt
   # (Opsiyonel) Drag & Drop desteği için:
   pip install tkinterdnd2
   ```

---

## 🖥️ Kullanım (Usage)

### Başlatma
Uygulama hem macOS hem Windows uyumludur.

**macOS:**
```bash
./Start_Mac.command
```

**Windows:**
```bash
Start_Win.bat
```

veya terminalden:
```bash
python run.py
```

### SHATTER Kullanımı
1. **Dosya Seç:** Parçalamak istediğiniz dosya veya klasörleri sürükleyip bırakın.
2. **Şifre Belirle:** Güçlü bir şifre girin.
3. **Parçala:** "HEPSİNİ PARÇALA" butonuna basın.
   - Sonuç: Orijinal dosya silinir (Secure Wipe seçilirse), yerine okunamaz `.enc` parçaları ve bir `.shatter_manifest` dosyası oluşturulur.
4. **Birleştirme:** `.shatter_manifest` dosyasını seçip şifrenizi girerek dosyayı orijinal haline döndürebilirsiniz.

---

## 🔒 Güvenlik Notları (Security Specs)

Bu proje "Surface Level" bir şifreleme aracı değildir. Aşağıdaki güvenlik standartlarını uygular:

| Özellik | Teknoloji | Açıklama |
| :--- | :--- | :--- |
| **Cipher** | ChaCha20-Poly1305 | Modern, yüksek performanslı AEAD şifreleme. |
| **KDF** | Argon2id v13 | GPU/ASIC saldırılarına dirençli (64MB RAM/Op). |
| **Randomness** | `secrets.token_bytes` | OS Cryptographic PRNG kullanımı. |
| **Integrity** | Poly1305 + HMAC | Veri değişikliği (bit-flip) anında tespit edilir. |
| **Key Wrap** | Context-Bound | Anahtarlar UUID ile mühürlenir, taşınamaz. |

> **NOT:** SSD/Flash depolama birimlerinde "Secure Wipe" (Güvenli Silme) işlemi, cihazın "Wear Leveling" teknolojisi nedeniyle fiziksel veriyi %100 silmeyebilir. Ancak SHATTER, dosyayı şifreleyerek parçaladığı ve *Anahtar İmhası (Cryptographic Erasure)* yaptığı için veri güvenliği matematiksel olarak sağlanır.

---

## ⚠️ Yasal Uyarı

Bu yazılım "OLDUĞU GİBİ" sunulmuştur. Yazar, bu yazılımın kullanımından doğabilecek veri kaybı veya hasarlardan sorumlu tutulamaz. Kritik verileriniz için her zaman yedek alınız.

---

## 📜 Lisans (License)
Bu proje **MIT Lisansı** ile lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

MIT License © 2025 Hellsyium (System Hub)

---

*Desiged & Hardened by Antigravity*
