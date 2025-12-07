import hashlib # [NEW] Added for integrity check

class FileTransferManager:
    """
    Manages P2P file transfers over WebRTC Data Channels.
    - Sender: Chunking, Metadata generation.
    - Receiver: Reassembly, Validation, Safe storage.
    """
    
    CHUNK_SIZE = 16 * 1024 # 16KB chunks (Safe for WebRTC DataChannel)
    DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "AetherReceived")

    def __init__(self, on_progress: Callable[[str, float, str], None], on_complete: Callable[[str, str], None]):
        """
        on_progress: (filename, percentage, status_text) -> None
        on_complete: (filename, full_path) -> None
        """
        self.on_progress = on_progress
        self.on_complete = on_complete
        
        # Incoming Transfers state: { file_id: { ... } }
        self.incoming_transfers = {}
        self.lock = threading.Lock()
        
        # Ensure download directory exists
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)

    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                data = f.read(65536) # 64KB chunks for hashing
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def prepare_upload(self, filepath: str) -> dict:
        """
        Prepares metadata for a file upload.
        Returns: Metadata JSON
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        file_id = str(uuid.uuid4())
        
        # Calculate Hash
        print(f"[FILE] Calculating hash for {filename}...")
        file_hash = self._calculate_file_hash(filepath)
        
        return {
            "type": "file_meta",
            "id": file_id,
            "name": filename,
            "size": filesize,
            "hash": file_hash, # [NEW] Send Hash
            "ts": time.time()
        }

    def read_chunks(self, filepath: str, file_id: str):
        """
        Generator that yields JSON chunks for the file.
        """
        file_size = os.path.getsize(filepath)
        bytes_sent = 0
        seq = 0
        
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                
                # Encode binary to Base64 for JSON transport (Optimize to binary later)
                b64_data = base64.b64encode(chunk).decode('ascii')
                
                msg = {
                    "type": "file_chunk",
                    "id": file_id,
                    "seq": seq,
                    "data": b64_data,
                    "end": False
                }
                
                yield msg
                
                bytes_sent += len(chunk)
                seq += 1
                
                # Progress update (Callback)
                progress = (bytes_sent / file_size) * 100
                self.on_progress(os.path.basename(filepath), progress, "Gönderiliyor...")

        # End of file marker
        yield {
            "type": "file_chunk",
            "id": file_id,
            "seq": seq,
            "data": "",
            "end": True
        }

    def handle_message(self, msg: dict):
        """Route incoming file messages."""
        msg_type = msg.get("type")
        
        if msg_type == "file_meta":
            self._handle_metadata(msg)
        elif msg_type == "file_chunk":
            self._handle_chunk(msg)

    def _sanitize_filename(self, filename: str) -> str:
        """Security: Remove path traversal chars."""
        safe_name = os.path.basename(filename)
        # TODO: Add more rigorous sanitization if needed
        return safe_name

    def _handle_metadata(self, meta: dict):
        """Start receiving a new file."""
        file_id = meta["id"]
        filename = self._sanitize_filename(meta["name"])
        filesize = meta["size"]
        file_hash = meta.get("hash", "") # [NEW] Get expected hash
        
        # Prevent duplicates or collisions by renaming if exists
        target_path = os.path.join(self.DOWNLOAD_DIR, filename)
        base, ext = os.path.splitext(target_path)
        counter = 1
        while os.path.exists(target_path):
            target_path = f"{base}_{counter}{ext}"
            counter += 1
            
        print(f"[FILE] Starting download: {filename} ({filesize} bytes)")
        
        with self.lock:
            self.incoming_transfers[file_id] = {
                "path": target_path,
                "name": os.path.basename(target_path),
                "total_size": filesize,
                "received_size": 0,
                "expected_seq": 0,
                "expected_hash": file_hash, # [NEW] Store expected
                "hasher": hashlib.sha256() if file_hash else None, # [NEW] Incremental hasher
                "file_handle": open(target_path, "wb")
            }
        
        self.on_progress(os.path.basename(target_path), 0, "İndirme Başladı...")

    def _handle_chunk(self, chunk: dict):
        """Write chunk to disk."""
        file_id = chunk["id"]
        
        with self.lock:
            if file_id not in self.incoming_transfers:
                return # Should send Error/NACK
            
            transfer = self.incoming_transfers[file_id]
            
            # Sequence Validation (Basic)
            # if chunk["seq"] != transfer["expected_seq"]:
            #     print(f"[FILE] Out of order chunk! Got {chunk['seq']}, expected {transfer['expected_seq']}")
            #     # In reliable transport (TCP/SCTP) this is rare, but good to know
            
            if chunk["end"]:
                # FINISH
                transfer["file_handle"].close()
                
                # [NEW] Verify Hash
                final_status = "Tamamlandı! ✅"
                if transfer["hasher"] and transfer["expected_hash"]:
                    calculated_hash = transfer["hasher"].hexdigest()
                    if calculated_hash != transfer["expected_hash"]:
                        print(f"[FILE] Hash Mismatch! Expected {transfer['expected_hash']}, Got {calculated_hash}")
                        final_status = "Hata: Dosya Bütünlüğü Bozuk ❌"
                        # rename to .corrupt?
                        new_path = transfer["path"] + ".corrupt"
                        os.rename(transfer["path"], new_path)
                        transfer["path"] = new_path
                    else:
                        print(f"[FILE] Hash Verified ✅")
                
                del self.incoming_transfers[file_id]
                self.on_progress(transfer["name"], 100, final_status)
                self.on_complete(transfer["name"], transfer["path"])
                print(f"[FILE] Download complete: {transfer['path']}")
                return

            # Decode and Write
            data = base64.b64decode(chunk["data"])
            transfer["file_handle"].write(data)
            
            # [NEW] Update Hash
            if transfer["hasher"]:
                transfer["hasher"].update(data)
            
            transfer["received_size"] += len(data)
            transfer["expected_seq"] += 1
            
            # Progress Logic
            if transfer["total_size"] > 0:
                percent = (transfer["received_size"] / transfer["total_size"]) * 100
                self.on_progress(transfer["name"], percent, f"İndiriliyor %{int(percent)}")
            
