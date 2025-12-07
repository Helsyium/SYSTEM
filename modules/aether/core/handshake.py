import socket
import json
import threading
import asyncio

class HandshakeManager:
    """
    Handles the TCP Handshake to exchange SDP automatically.
    - Server: Waits for incoming connection -> Receives Offer -> Sends Answer.
    - Client: Connects to peer -> Sends Offer -> Receives Answer.
    """
    
    def __init__(self, callback_on_offer, port=0):
        """
        callback_on_offer: Function(offer_json) -> answer_json (Async)
        port: 0 for random available port
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("", port))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        
        self.running = True
        self.callback_on_offer = callback_on_offer # Must return Answer JSON
        
        # Start Listener Thread
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        
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
            
            print("[HANDSHAKE] Offer received. Generating answer...")
            
            # 3. Generate Answer (using callback into App logic)
            # Since callback is likely async/GUI, we need to wait for result.
            # This is tricky because App is in Main Thread/Async Loop.
            # Ideally callback should handle thread sync.
            answer_json = self.callback_on_offer(offer_json)
            
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
            s.settimeout(5)
            s.connect((ip, port))
            
            # 1. Send Offer
            payload = json.dumps(offer_json).encode('utf-8')
            s.send(len(payload).to_bytes(4, 'big'))
            s.send(payload)
            
            # 2. Receive Answer
            header = s.recv(4)
            if not header: raise ValueError("No response from peer")
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
