# SYSTEM HUB - Secure Digital Vault & File Sharding Engine

**SYSTEM HUB** is a modular security platform designed for personal data protection. It delivers **military-grade encryption** and **cryptographic file sharding** technologies through a user-friendly, modern interface.

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Security](https://img.shields.io/badge/Security-Hardened%20v3.5-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Modules

The project consists of two powerful modules under a single roof:

### 1. 🛡️ VAULT (Folder Locker)
Encrypts and hides your folders in seconds.
- **AES-256-GCM** encryption.
- **Scrypt** KDF (Key Derivation Function) for brute-force protection.
- Encrypts filenames and directory structures for complete privacy.

### 2. 🧩 SHATTER v3.5 (File Sharding Engine)
Encrypts your files and fragments them into thousands of meaningless pieces.
- **ChaCha20-Poly1305** (AEAD) encryption.
- **Argon2id** (64MB, 2-Pass) memory-hard KDF.
- **Shard-Level Encryption:** Each fragment is encrypted with a *unique* 32-byte key.
- **Deterministic Nonce Strategy:** `HMAC-SHA256` based nonce generation (0% Collision).
- **Context-Bound Key Wrapping:** Chunk keys are never stored raw; they are sealed with the Master Key and Chunk UUID (Protected against "Cut-and-Paste" attacks).
- **Atomic I/O:** Prevents data corruption during power failures.

---

## 🛠️ Installation

### Requirements
- Python 3.10+
- `pip`

### Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Helsyium/SYSTEM
   cd SYSTEM
   ```

2. **Install Dependencies:**
   ```bash
   # Create Virtual Environment (Recommended)
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   venv\Scripts\activate     # Windows

   # Install Packages
   pip install -r requirements.txt
   # (Optional) For Drag & Drop support:
   pip install tkinterdnd2
   ```

---

## 🖥️ Usage

### Launching
The application is compatible with both macOS and Windows.

**macOS:**
```bash
./Start_Mac.command
```

**Windows:**
```bash
Start_Win.bat
```

Or via terminal:
```bash
python run.py
```

### SHATTER Usage
1. **Select File:** Drag and drop the file or folder you want to shatter.
2. **Set Password:** Enter a strong password.
3. **Shatter:** Click "SHATTER ALL".
   - Result: The original file is securely deleted (if requested), replaced by unreadable `.enc` shards and a `.shatter_manifest` file.
4. **Reassemble:** Select the `.shatter_manifest` file and enter your password to restore the original file.

---

## 🔒 Security Specs

This project is not a "Surface Level" encryption tool. It implements the following security standards:

| Feature | Technology | Description |
| :--- | :--- | :--- |
| **Cipher** | ChaCha20-Poly1305 | Modern, high-performance AEAD encryption. |
| **KDF** | Argon2id v13 | Resistant to GPU/ASIC attacks (64MB RAM/Op). |
| **Randomness** | `secrets.token_bytes` | Uses OS Cryptographic PRNG. |
| **Integrity** | Poly1305 + HMAC | Detects data modification (bit-flip) instantly. |
| **Key Wrap** | Context-Bound | Keys are sealed with UUIDs, non-transferable. |

> **NOTE:** On SSD/Flash storage, "Secure Wipe" may not guarantee 100% physical erasure due to Wear Leveling. However, SHATTER ensures data security mathematically via **Cryptographic Erasure** (destroying the keys).

---

## ⚠️ Disclaimer

This software is provided "AS IS", without warranty of any kind. The author is not responsible for any data loss or damages arising from the use of this software. Always backup critical data.

---

## 📜 License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

MIT License © 2025 Hellsyium (System Hub)

---

*Designed & Hardened by Antigravity*
