import socket
import threading
import time
import json
import uuid
import logging
from typing import Callable, Dict

# Configuration
BROADCAST_IP = "255.255.255.255"
DISCOVERY_PORT = 50005
BEACON_INTERVAL = 2.0  # Seconds

class NetworkDiscovery:
    """
    Serverless Local Network Discovery using UDP Broadcast.
    - Broadcaster: Sends 'I am here' beacons.
    - Listener: Listens for beacons from other peers.
    """
    
    def __init__(self, username: str, tcp_port: int):
        self.device_id = str(uuid.uuid4())
        self.username = username
        self.tcp_port = tcp_port # Port for Handshake
        self.running = False
        self.peers: Dict[str, dict] = {} # {device_id: info_dict}
        self.on_peer_found: Callable = None
        self.on_peer_lost: Callable = None
        
        # Sockets
        self.sock_broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.sock_listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Threads
        self.thread_broadcast = None
        self.thread_listen = None
        
    def start(self):
        self.running = True
        try:
            # Bind to all interfaces
            self.sock_listen.bind(("", DISCOVERY_PORT))
        except Exception as e:
            print(f"[DISCOVERY] Bind failed (Port {DISCOVERY_PORT} busy?): {e}")
            return

        self.thread_broadcast = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.thread_listen = threading.Thread(target=self._listen_loop, daemon=True)
        
        self.thread_broadcast.start()
        self.thread_listen.start()
        print(f"[DISCOVERY] Started. My ID: {self.device_id[:8]}")

    def stop(self):
        self.running = False
        try:
            self.sock_broadcast.close()
            self.sock_listen.close()
        except:
            pass

    def _broadcast_loop(self):
        """Periodically broadcast presence."""
        while self.running:
            try:
                msg = {
                    "aether_version": "1.0",
                    "id": self.device_id,
                    "user": self.username,
                    "port": self.tcp_port,
                    "ts": time.time()
                }
                data = json.dumps(msg).encode('utf-8')
                self.sock_broadcast.sendto(data, (BROADCAST_IP, DISCOVERY_PORT))
            except Exception as e:
                # print(f"[DISCOVERY] Broadcast error: {e}")
                pass
            
            time.sleep(BEACON_INTERVAL)

    def _listen_loop(self):
        """Listen for UDP beacons."""
        while self.running:
            try:
                data, addr = self.sock_listen.recvfrom(1024)
                ip = addr[0]
                
                # Ignore own packets (if loopback) - logic handled by ID check
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get("id") == self.device_id:
                    continue # It's me
                
                # Handle Peer Found
                self._handle_peer(ip, msg)
                
            except Exception as e:
                if self.running:
                    print(f"[DISCOVERY] Listen error: {e}")
                break

    def _handle_peer(self, ip, msg):
        peer_id = msg["id"]
        is_new = peer_id not in self.peers
        
        # Update peer info
        self.peers[peer_id] = {
            "ip": ip,
            "port": msg["port"],
            "user": msg["user"],
            "last_seen": time.time()
        }
        
        if is_new:
            print(f"[DISCOVERY] New Peer Found: {msg['user']} ({ip})")
            if self.on_peer_found:
                self.on_peer_found(self.peers[peer_id])
                
    def get_peers(self):
        # Prune old peers (> 10s)
        now = time.time()
        active_peers = []
        to_remove = []
        
        for pid, pdata in self.peers.items():
            if now - pdata["last_seen"] > 10:
                to_remove.append(pid)
            else:
                active_peers.append(pdata)
                
        for pid in to_remove:
            del self.peers[pid]
            # Optionally trigger on_peer_lost
            
        return active_peers
