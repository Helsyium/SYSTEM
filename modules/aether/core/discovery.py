import socket
import threading
import time
import json
import uuid
import logging
from typing import Callable, Dict

import os

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
    
    def __init__(self, username: str, tcp_port: int, storage_dir: str = None):
        self.storage_dir = storage_dir or os.getcwd()
        self.device_id = self._load_or_create_device_id()
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

    def _load_or_create_device_id(self):
        """Load persistent device ID or create new one."""
        id_file = os.path.join(self.storage_dir, "aether_identity.json")
        if os.path.exists(id_file):
            try:
                with open(id_file, "r") as f:
                    data = json.load(f)
                    return data.get("device_id", str(uuid.uuid4()))
            except:
                pass
        
        new_id = str(uuid.uuid4())
        try:
            with open(id_file, "w") as f:
                json.dump({"device_id": new_id}, f)
        except:
            pass
        return new_id
        
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
                sender_ip = addr[0]
                
                # Decode
                try:
                    msg = json.loads(data.decode('utf-8'))
                except:
                    continue

                # 1. Self Check by ID (Robust)
                if msg.get("id") == self.device_id:
                    continue 

                # 2. Self Check by IP (Optional backup, but ID is better)
                # We skip this because we might rely on ID if NAT makes IPs weird.
                
                # Handle Peer Found
                self._handle_peer(sender_ip, msg)
                
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
