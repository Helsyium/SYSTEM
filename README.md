# SYSTEM HUB - Secure Digital Vault & File Sharding Engine

**SYSTEM HUB** is an advanced, modular security platform designed for uncompromising personal data protection. It integrates **ChaCha20-Poly1305 (IETF)** encryption and innovative **cryptographic file sharding** technologies through a modern, responsive interface.

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Security](https://img.shields.io/badge/Security-Hardened%20v3.5-blue)
![Architecture](https://img.shields.io/badge/Architecture-Modular-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Core Modules

### 1. 🛡️ VAULT (Folder Locker)
A high-performance directory encryption module.
- **Algorithm:** **ChaCha20-Poly1305** (Authenticated Encryption). *Surpasses AES-256 in software performance on mobile/legacy CPUs.*
- **Key Derivation (KDF):** **Scrypt** (N=16384, r=8, p=1).
- **Features:** Encrypts filenames, directory structures, and file contents. Zero-knowledge architecture.

### 2. 🧩 SHATTER v3.5 (File Sharding Engine)
The flagship module of SYSTEM HUB. It implements a unique "Sharding & Encryption" strategy to secure files against advanced forensic analysis and "Cut-and-Paste" attacks.

#### 🔐 Technical Architecture & Security Hardening (v3.5)

SHATTER v3.5 is built upon a **Defense-in-Depth** philosophy. It is not just an encryption tool; it is a data fragmentation system.

| Component | Specification | Rationale |
| :--- | :--- | :--- |
| **Cipher** | **ChaCha20-Poly1305** | High-performance AEAD (Authenticated Encryption with Associated Data). Offers superior software performance compared to AES on mobile/legacy CPUs without hardware acceleration. |
| **KDF (Master)** | **Argon2id** (v13) | Configured with `64MB Memory`, `2 Passes`, `2 Parallelism`. Resistant to GPU/ASIC brute-force attacks. |
| **Nonce Strategy** | **Deterministic (HMAC-SHA256)** | `Nonce = HMAC-SHA256(Key, ChunkIndex)[:12]`. Eliminated `os.urandom` for nonces to mathematically guarantee **0% collision risk**, vital for the 96-bit nonce space of ChaCha20. |
| **Key Management** | **Context-Bound Key Wrapping** | Chunk Keys are **never** stored in plaintext. They are wrapped (encrypted) using the Master Key. <br> `Wrap = Encrypt(MasterKey, ChunkKey, AD=ChunkUUID)`. |
| **Integrity** | **AEAD + Context Binding** | During decryption, the `ChunkUUID` is passed as Associated Data (AD). If a chunk is moved to another manifest (Cut-and-Paste attack), decryption fails instantly. |
| **Randomness** | **secrets.token_bytes** | Uses the operating system's CSPRNG for all Salt and Key generation (replaced `os.urandom` for strict cryptographic compliance). |
| **I/O Safety** | **Atomic Write (fsync)** | All chunks and manifests are written to temporary files and renamed only after `fsync` ensures disk persistence. Prevents corruption during power loss. |

#### 🔄 Workflow
1.  **Fragmentation:** Input file is divided into variable-sized chunks (1MB - 50MB based on total size).
2.  **Key Gen:** A unique 32-byte key is generated for *each* chunk.
3.  **Encryption:** Each chunk is encrypted independently using ChaCha20-Poly1305.
4.  **Manifest Construction:** A protected JSON manifest is created, containing encrypted chunk keys (wrapped) and metadata. The manifest itself is then encrypted with the Master Key.
5.  **Secure Wipe:** Original file is overwritten with random data (Cryptographic Erasure concept applied for SSDs).

### 3. 🌩️ AETHER (P2P Mesh Network)
A decentralized, serverless communication module designed for secure, censorship-resistant connectivity.

- **Technology:** WebRTC (via `aiortc`), DTLS/SRTP Encryption, UDP Broadcast Discovery.
- **Topology:** Hybrid Peer-to-Peer (LAN & WAN).
- **Features:**
    - **Hybrid Connectivity:**
        - **🏠 Same WiFi (LAN):** Automatic serverless discovery of nearby peers via UDP Broadcast. One-click connection without codes.
        - **🌍 Different WiFi (WAN):** Manual "Out-of-Band" signaling (Copy-Paste Offer/Answer) for connecting devices across the internet without central servers.
    - **Serverless & Private:** No central signaling server, no database, no metadata retention.
    - **NAT Traversal:** STUN support for connectivity behind firewalls.
    - **Cross-Platform:** Seamless communication between macOS and Windows.
    - **Non-Intrusive:** Works without requiring aggressive administrator privileges or complex firewall scripts.

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
   # Create Virtual Environment
   python -m venv venv
   # Activate
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows

   # Install
   pip install -r requirements.txt
   ```

---

## 🖥️ Usage

**macOS:**
```bash
./Start_Mac.command
```
**Windows:**
```bash
Start_Win.bat
```

---

## ⚠️ Disclaimer
This software is provided "AS IS", without warranty of any kind. While it implements state-of-the-art cryptographic primitives, the author is not responsible for data loss or damages. **Always backup critical data.**

## 📜 License
MIT License © 2025 Hellsyium (System Hub)
