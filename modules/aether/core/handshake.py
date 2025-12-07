import socket
import json
import threading
import asyncio
from collections import deque
import time

class HandshakeManager:
    """
    Handles the TCP Handshake to exchange SDP automatically.
    - Server: Waits for incoming connection -> Receives Offer -> Sends Answer.
    - Client: Connects to peer -> Sends Offer -> Receives Answer.
    """
    
    def __init__(self, callback_on_offer, port=0):
        """
        callback_on_offer: Function(offer_json) -> answer_json (Async)
        port: 0 for random available port, BUT we will try 54000 range first for stability.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Try to bind to a fixed port range (54000-54010) for persistence
        # This allows cached Trusted Peers to reconnect even after app restart
        bound = False
        start_port = 54000
        for p in range(start_port, start_port + 10):
            try:
                # Explicitly bind to IPv4 ANY address (0.0.0.0)
                # Binding to "" can sometimes defaut to IPv6 or localhost only on Windows
                self.sock.bind(("0.0.0.0", p))
                bound = True
                break
            except OSError:
                continue
        
        if not bound:
            # Fallback to random port if all fixed ones are taken
            self.sock.bind(("0.0.0.0", 0))
            
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        
        self.running = True
        self.callback_on_offer = callback_on_offer # Must return Answer JSON
        
        # Anti-Replay: Track processed offer IDs/Nonces
        # A simple deque to store last 1000 message hashes or nonces
        self.processed_nonces = deque(maxlen=1000)
        self.processed_nonces_lock = threading.Lock()
        
        # Start UPnP Port Mapping in Background
        threading.Thread(target=self._setup_upnp, daemon=True).start()
        
        # Start Listener Thread
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        
    def _setup_upnp(self):
        """Attempts to open the TCP port on the Router via UPnP."""
        try:
            from modules.aether.core.upnp import UPnPManager
            upnp = UPnPManager()
            if upnp.discover():
                print(f"[AETHER UPnP] Gateway found at {upnp.gateway_url}")
                # Try to map external port same as local port
                success = upnp.add_port_mapping(self.port, self.port, "TCP", description="Aether P2P Handshake")
                if success:
                    print(f"[AETHER UPnP] SUCCESS! Port {self.port} is now open to WAN.")
                else:
                    print(f"[AETHER UPnP] Failed to add port mapping.")
            else:
                print(f"[AETHER UPnP] No UPnP Gateway found.")
        except Exception as e:
            print(f"[AETHER UPnP] Error: {e}")
        
    def _accept_loop(self):
        print(f"[HANDSHAKE] Listening on TCP {self.port}")
        while self.running:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,)).start()
            except:
                break
                
    def _handle_client(self, conn):
        """Handle incoming connection (Process Offer)."""
        try:
            print(f"[HANDSHAKE] Incoming connection from {conn.getpeername()}")
            # 1. Receive Offer Size
            header = conn.recv(4)
            if not header: return
            length = int.from_bytes(header, 'big')
            
            # 2. Receive Offer JSON
            data = b""
            while len(data) < length:
                chunk = conn.recv(4096)
                if not chunk: break
                data += chunk
                
            offer_str = data.decode('utf-8')
            offer_json = json.loads(offer_str)
            
            # === ANTI-REPLAY CHECK ===
            # We expect a 'nonce' or unique ID in top level of offer_json for security v2
            # If missing, we generate a hash of the content as a fallback nonce (less secure but works)
            nonce = offer_json.get("nonce")
            if not nonce:
                # Fallback: Hash of SDP gives some dedup ability
                import hashlib
                nonce = hashlib.sha256(offer_str.encode()).hexdigest()
            
            with self.processed_nonces_lock:
                if nonce in self.processed_nonces:
                    print(f"[HANDSHAKE] REPLAY DETECTED. Dropping duplicate offer. Nonce: {nonce[:8]}...")
                    return # Silently drop or send error
                self.processed_nonces.append(nonce)
            # =========================
            
            print("[HANDSHAKE] Offer received. Generating answer...")
            
            # 3. Generate Answer (using callback into App logic)
            # Since callback is likely async/GUI, we need to wait for result.
            # This is tricky because App is in Main Thread/Async Loop.
            # Ideally callback should handle thread sync.
            answer_json = self.callback_on_offer(offer_json)
            
            # Handle case where app is busy (returns None)
            if answer_json is None:
                print("[HANDSHAKE] Server busy, connection rejected")
                conn.send(b"BUSY")
                return
            
            # 4. Send Answer
            answer_bytes = json.dumps(answer_json).encode('utf-8')
            conn.send(len(answer_bytes).to_bytes(4, 'big'))
            conn.send(answer_bytes)
            print("[HANDSHAKE] Answer sent.")
            
        except Exception as e:
            print(f"[HANDSHAKE] Server Error: {e}")
        finally:
            conn.close()

    def connect_and_exchange(self, ip, port, offer_json):
        """
        Client side: Connect to peer, send offer, get answer.
        Returns: Answer JSON (dict)
        """
        try:
            print(f"[HANDSHAKE] Connecting to {ip}:{port}...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)  # Increased from 5s to 10s for slower networks/firewalls
            
            try:
                s.connect((ip, port))
            except socket.timeout:
                raise Exception(f"Connection timed out. Windows Firewall might be blocking port {port}. Please check firewall settings.")
            except ConnectionRefusedError:
                raise Exception(f"Connection refused. Peer might not be listening on port {port}.")
            
            # 1. Send Offer
            payload = json.dumps(offer_json).encode('utf-8')
            s.send(len(payload).to_bytes(4, 'big'))
            s.send(payload)
            
            # 2. Receive Answer
            s.settimeout(15)  # Give more time for answer generation (WebRTC can be slow)
            header = s.recv(4)
            if not header: raise ValueError("No response from peer (empty header)")
            
            # Check for BUSY signal
            if header == b"BUSY":
                raise Exception("Peer is busy with another connection. Please wait and try again.")
            
            length = int.from_bytes(header, 'big')
            
            data = b""
            while len(data) < length:
                chunk = s.recv(4096)
                if not chunk: break
                data += chunk
                
            answer_str = data.decode('utf-8')
            s.close()
            
            return json.loads(answer_str)
            
        except Exception as e:
            print(f"[HANDSHAKE] Client Error: {e}")
            raise e
            
    def stop(self):
        self.running = False
        self.sock.close()
