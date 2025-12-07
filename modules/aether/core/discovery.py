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
        self.tcp_port = tcp_port
        self.running = False
        self.peers: Dict[str, dict] = {} 
        self.on_peer_found: Callable = None
        
        # Sockets
        self.sock_broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.sock_listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Mac/Linux specific optimization
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except:
                pass

        # Threads
        self.thread_broadcast = None
        self.thread_listen = None

    def _get_local_ip_and_broadcast(self):
        """Determine Local IP and subnet-specific broadcast address."""
        try:
            # Connect to a public DNS to find the primary interface (no data sent)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Simple /24 assumption for home networks (192.168.1.x -> 192.168.1.255)
            # This is much more reliable on Windows than 255.255.255.255
            parts = local_ip.split('.')
            parts[3] = '255'
            broadcast_ip = '.'.join(parts)
            return local_ip, broadcast_ip
        except:
            return "127.0.0.1", "255.255.255.255"

    def _broadcast_loop(self):
        """Periodically broadcast presence."""
        while self.running:
            try:
                local_ip, broadcast_target = self._get_local_ip_and_broadcast()
                
                msg = {
                    "aether_version": "1.0",
                    "id": self.device_id,
                    "user": self.username,
                    "ip": local_ip, # Send explicit IP
                    "port": self.tcp_port,
                    "ts": time.time()
                }
                data = json.dumps(msg).encode('utf-8')
                
                # Send to Directed Broadcast (Address specific subnet)
                self.sock_broadcast.sendto(data, (broadcast_target, DISCOVERY_PORT))
                
                # Also send to General Broadcast (Fallback)
                self.sock_broadcast.sendto(data, ("255.255.255.255", DISCOVERY_PORT))
                
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
