import customtkinter as ctk
import asyncio
import threading
import json
import logging
import os # Added global import
from tkinter import messagebox

# Monkey Patch for av <-> aiortc compatibility
try:
    import av
    if not hasattr(av, 'AudioCodecContext') and hasattr(av, 'CodecContext'):
        av.AudioCodecContext = av.CodecContext
except ImportError:
    pass

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel, RTCConfiguration, RTCIceServer
from system.core.config import THEME

class AetherApp(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.loop = asyncio.new_event_loop()
        self.pc = None
        self.channel = None
        self.is_running = True
        self.connection_lock = threading.Lock()  # Prevent reconnection race conditions
        
        # Start AsyncIO Loop in a separate thread
        self.thread = threading.Thread(target=self.start_loop, daemon=True)
        self.thread.start()

        # --- AETHER AUTOMATION MODULES ---
        from modules.aether.core.discovery import NetworkDiscovery
        from modules.aether.core.handshake import HandshakeManager
        import platform # For hostname defaults

        # 1. Start Handshake Server (TCP) - Listens for incoming Offers
        self.handshake = HandshakeManager(callback_on_offer=self.handle_incoming_offer_auto)
        
        # 2. Start Discovery (UDP) - Broadcasts our TCP Port
        my_hostname = platform.node()
        
        # Determine storage path for identity persistence
        import os
        aether_data_dir = os.path.join(os.getcwd(), "modules", "aether", "data")
        os.makedirs(aether_data_dir, exist_ok=True)

        self.discovery = NetworkDiscovery(username=my_hostname, tcp_port=self.handshake.port, storage_dir=aether_data_dir)
        self.discovery.on_peer_found = self.on_peer_found_callback
        self.discovery.start()
        
        # Load Trusted Peers
        self.trusted_peers_file = os.path.join(aether_data_dir, "trusted_peers.json")
        self.trusted_peers = self.load_trusted_peers()

        # Store peers locally for UI mapping
        self.known_peers = {} # {display_string: peer_data}

        # GUI Setup
        self.setup_ui()
        
        # Bind cleanup to app destruction
        self.bind("<Destroy>", self.on_app_destroy)

    def load_trusted_peers(self):
        if os.path.exists(self.trusted_peers_file):
            try:
                with open(self.trusted_peers_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_trusted_peer(self, peer_data):
        pid = peer_data["id"]
        self.trusted_peers[pid] = {
            "user": peer_data["user"],
            "last_ip": peer_data["ip"],
            "last_port": peer_data.get("port"),
            "trusted": True
        }
        try:
            with open(self.trusted_peers_file, "w") as f:
                json.dump(self.trusted_peers, f, indent=4)
        except Exception as e:
            print(f"Error saving trusted peers: {e}")


    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        """Schedule an async task in the loop thread"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def setup_ui(self):
        """Refactored UI with 3 Main Options."""
        self.main_container = ctk.CTkFrame(self.master, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # TITLE
        self.lbl_title = ctk.CTkLabel(self.main_container, text="AETHER P2P AĞI", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=(0, 20))

        # --- FRAMES ---
        # 1. Home Menu (3 Options)
        self.frame_home = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # 2. Sub-Panels
        self.frame_discovery = ctk.CTkFrame(self.main_container) # Same Wi-Fi
        self.frame_manual = ctk.CTkFrame(self.main_container)    # Different Wi-Fi
        self.frame_trusted = ctk.CTkFrame(self.main_container)   # Trusted Peers
        self.frame_chat = ctk.CTkFrame(self.main_container)      # Valid Connected Session
        
        # Build Navigation
        self.build_home_menu()
        self.build_discovery_panel()
        self.build_manual_panel()
        self.build_trusted_panel()
        self.build_chat_panel()

        # Show Home by default
        self.show_home()

    def build_home_menu(self):
        """Create the 3 main option buttons."""
        # Option 1: Same Wi-Fi (Auto)
        btn_wifi = ctk.CTkButton(self.frame_home, text="🏠 AYNI WI-FI (OTOMATİK)", 
                                 command=self.show_discovery_panel,
                                 height=60, font=("Roboto", 16, "bold"), fg_color=THEME["colors"]["accent"], text_color="black")
        btn_wifi.pack(fill="x", pady=10)
        
        # Option 2: Different Wi-Fi (Manual)
        btn_manual = ctk.CTkButton(self.frame_home, text="🌍 FARKLI AĞ (MANUEL / WAN)", 
                                   command=self.show_manual_panel,
                                   height=60, font=("Roboto", 16, "bold"), fg_color=THEME["colors"]["bg_card"])
        btn_manual.pack(fill="x", pady=10)

        # Option 3: Trusted Devices
        btn_trusted = ctk.CTkButton(self.frame_home, text="⭐ GÜVENİLİR CİHAZLAR", 
                                    command=self.show_trusted_panel,
                                    height=60, font=("Roboto", 16, "bold"), fg_color=THEME["colors"]["success"], text_color="black")
        btn_trusted.pack(fill="x", pady=10)

    def go_back(self):
        """Wait/Hide all and show Home."""
        self.frame_discovery.pack_forget()
        self.frame_manual.pack_forget()
        self.frame_trusted.pack_forget()
        self.frame_chat.pack_forget()
        self.lbl_title.configure(text="AETHER P2P AĞI", text_color="white")
        self.show_home()

    def show_home(self):
        self.frame_home.pack(fill="both", expand=True)

    def show_discovery_panel(self):
        self.frame_home.pack_forget()
        self.frame_discovery.pack(fill="both", expand=True)
        # Refresh discovery UI mapping if needed
        
    def show_manual_panel(self):
        self.frame_home.pack_forget()
        self.frame_manual.pack(fill="both", expand=True)

    def show_trusted_panel(self):
        self.frame_home.pack_forget()
        self.frame_trusted.pack(fill="both", expand=True)
        self.refresh_trusted_ui()
    
    def build_discovery_panel(self):
        """Panel for Local Network Discovery."""
        # Back Button
        ctk.CTkButton(self.frame_discovery, text="← GERİ", command=self.go_back, width=80, fg_color="gray").pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.frame_discovery, text="YAKINDAKİ CİHAZLAR (LAN)", font=("Roboto", 14, "bold")).pack(pady=10)
        
        self.scroll_peers = ctk.CTkScrollableFrame(self.frame_discovery, height=300, fg_color="transparent")
        self.scroll_peers.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.lbl_no_peers = ctk.CTkLabel(self.scroll_peers, text="Taranıyor...", text_color="gray")
        self.lbl_no_peers.pack(pady=20)

    def build_manual_panel(self):
        """Panel for Manual Host/Join (Traditional)."""
        # Back Button
        ctk.CTkButton(self.frame_manual, text="← GERİ", command=self.go_back, width=80, fg_color="gray").pack(anchor="w", pady=5)
        
        # Mode Selection (Host/Join)
        self.frame_modes = ctk.CTkFrame(self.frame_manual, fg_color="transparent")
        self.frame_modes.pack(fill="x", pady=10)
        
        self.btn_host = ctk.CTkButton(self.frame_modes, text="BAĞLANTI BAŞLAT (HOST)", command=self.show_host_mode,
                                      fg_color=THEME["colors"]["accent"], text_color="black", height=50)
        self.btn_host.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_join = ctk.CTkButton(self.frame_modes, text="BAĞLAN (JOIN)", command=self.show_join_mode,
                                      fg_color=THEME["colors"]["bg_card_hover"], height=50)
        self.btn_join.pack(side="right", fill="x", expand=True, padx=5)

        # Signaling Area (Dynamic content for manual mode)
        self.frame_signaling = ctk.CTkFrame(self.frame_manual)
        self.frame_signaling.pack(fill="both", expand=True, pady=10)
        self.frame_signaling.pack_forget() # Initially hidden until host/join click

    def build_trusted_panel(self):
        """Panel for Trusted Devices."""
        ctk.CTkButton(self.frame_trusted, text="← GERİ", command=self.go_back, width=80, fg_color="gray").pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.frame_trusted, text="GÜVENİLİR CİHAZLAR", font=("Roboto", 14, "bold")).pack(pady=10)
        
        self.scroll_trusted = ctk.CTkScrollableFrame(self.frame_trusted, height=300, fg_color="transparent")
        self.scroll_trusted.pack(fill="both", expand=True, padx=5, pady=5)
        
    def refresh_trusted_ui(self):
        for widget in self.scroll_trusted.winfo_children():
            widget.destroy()
            
        if not self.trusted_peers:
            ctk.CTkLabel(self.scroll_trusted, text="Henüz güvenilir cihaz yok.", text_color="gray").pack(pady=20)
            return

        for pid, data in self.trusted_peers.items():
            card = ctk.CTkFrame(self.scroll_trusted, fg_color=THEME["colors"]["bg_card"])
            card.pack(fill="x", pady=5)
            
            # Check if peer is currently online in discovery
            live_peer = self.discovery.peers.get(pid) if hasattr(self, 'discovery') else None
            
            status_text = "🟢 ÇEVRİMİÇİ" if live_peer else "⚫ ÇEVRİMDIŞI"
            user_text = f"{data.get('user', 'Unknown')} ({data.get('last_ip', '?')}) {status_text}"
            
            lbl = ctk.CTkLabel(card, text=user_text, font=("Roboto", 12, "bold"))
            lbl.pack(side="left", padx=10, pady=10)
            
            # Connect button - use live peer data if available, otherwise use cached data
            if live_peer:
                # Peer is online, use current discovery info
                btn = ctk.CTkButton(card, text="BAĞLAN", width=80, 
                                    command=lambda p=live_peer, i=pid: self.start_auto_connection({**p, "id": i}),
                                    fg_color=THEME["colors"]["success"])
            else:
                # Peer offline, disable button or show warning
                btn = ctk.CTkButton(card, text="ÇEVRİMDIŞI", width=80, state="disabled",
                                    fg_color="gray")
            btn.pack(side="right", padx=10)

    def build_chat_panel(self):
        self.frame_chat.columnconfigure(0, weight=1)
        self.frame_chat.rowconfigure(0, weight=1)
        
        self.txt_chat_history = ctk.CTkTextbox(self.frame_chat, state="disabled", wrap="word")
        self.txt_chat_history.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.entry_message = ctk.CTkEntry(self.frame_chat, placeholder_text="Mesaj yaz...")
        self.entry_message.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_message.bind("<Return>", self.send_message)
        
        self.btn_send = ctk.CTkButton(self.frame_chat, text="GÖNDER", command=self.send_message, fg_color=THEME["colors"]["accent"], text_color="black")
        self.btn_send.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Close Chat / Disconnect
        ctk.CTkButton(self.frame_chat, text="BAĞLANTIYI KES", command=self.cleanup_and_home, fg_color="red").grid(row=3, column=0, pady=5)

    def cleanup_and_home(self):
        self.cleanup()
        self.go_back()
    def create_pc(self):
        # Use multiple STUN servers for better reliability
        stun_servers = [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
            "stun:stun2.l.google.com:19302",
            "stun:stun3.l.google.com:19302",
            "stun:stun4.l.google.com:19302",
            "stun:stun.services.mozilla.com:3478",
            "stun:global.stun.twilio.com:3478"
        ]
        
        config = RTCConfiguration(
            iceServers=[RTCIceServer(urls=stun_servers)]
        )
        pc = RTCPeerConnection(configuration=config)
        
        @pc.on("icegatheringstatechange")
        async def on_icegatheringstatechange():
            print(f"[AETHER DEBUG] ICE gathering state: {pc.iceGatheringState}")
        
        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            state = pc.iceConnectionState
            print(f"[AETHER DEBUG] ICE state: {state}")
            self.update_status(f"ICE Durumu: {state}")
            
            # Handle failed/disconnected states
            if state == "failed":
                self.master.after(0, lambda: self.handle_connection_failure("ICE bağlantısı başarısız"))
            elif state == "disconnected":
                # Give it 5 seconds to reconnect before declaring failure
                await asyncio.sleep(5)
                if pc.iceConnectionState == "disconnected":
                    self.master.after(0, lambda: self.handle_connection_failure("Bağlantı kesildi"))
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            state = pc.connectionState
            print(f"[AETHER DEBUG] Connection state: {state}")
            self.update_status(f"Bağlantı Durumu: {state}")
            
            if state == "failed":
                self.master.after(0, lambda: self.handle_connection_failure("WebRTC bağlantısı başarısız"))
            elif state == "closed":
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", "Bağlantı kapandı. 🔴"))
        
        return pc
    
    def handle_connection_failure(self, reason):
        """Handle connection failure with user notification."""
        if not hasattr(self, 'connection_failed_notified'):
            self.connection_failed_notified = True
            self.add_chat_message("SYSTEM", f"⚠️ {reason}")
            
            # Offer to reconnect
            if messagebox.askyesno("Bağlantı Sorunu", f"{reason}\n\nTekrar bağlanmayı denemek ister misin?"):
                # Clear flag and attempt reconnect
                del self.connection_failed_notified
                # TODO: Implement auto-reconnect logic
                self.add_chat_message("SYSTEM", "Otomatik yeniden bağlanma yakında eklenecek...")
            else:
                self.cleanup_and_home()

    def update_status(self, text):
        def _update():
            # Safe check for UI existence
            if not self.winfo_exists(): return
            
            # Check if lbl_status exists
            if hasattr(self, 'lbl_status') and self.lbl_status.winfo_exists():
                color = "yellow"
                if "connect" in text.lower():
                    color = THEME["colors"]["success"]
                elif "fail" in text.lower() or "close" in text.lower():
                    color = THEME["colors"]["danger"]
                elif "check" in text.lower():
                    color = "orange"
                self.lbl_status.configure(text=text, text_color=color)
            else:
                # Fallback to Title if we are in Auto-Mode (where lbl_status might not exist)
                # But only for major events to avoid spamming title
                print(f"[AETHER STATUS] {text}")
                if "connect" in text.lower() and hasattr(self, 'lbl_title'):
                     self.lbl_title.configure(text=f"AETHER: {text}", text_color=THEME["colors"]["success"])

        try:
            self.master.after(0, _update)
        except:
            pass

    # --- HOST MODE ---
    def show_host_mode(self):
        self.frame_modes.pack_forget()
        self.frame_signaling.pack(fill="both", expand=True, pady=10)
        
        # UI Elements for Host
        self.lbl_status = ctk.CTkLabel(self.frame_signaling, text="Durum: Bekleniyor...", font=("Roboto", 14, "bold"), text_color="yellow")
        self.lbl_status.pack(pady=(0, 10))

        self.lbl_step1 = ctk.CTkLabel(self.frame_signaling, text="ADIM 1: Bu Kodu Kopyala ve Karşı Tarafa Gönder")
        self.lbl_step1.pack(pady=5)
        
        self.txt_offer = ctk.CTkTextbox(self.frame_signaling, height=100)
        self.txt_offer.pack(fill="x", padx=10, pady=5)
        
        self.lbl_step2 = ctk.CTkLabel(self.frame_signaling, text="ADIM 2: Karşı Taraftan Gelen Cevabı (Answer) Buraya Yapıştır")
        self.lbl_step2.pack(pady=5)
        
        self.txt_answer_input = ctk.CTkTextbox(self.frame_signaling, height=100)
        self.txt_answer_input.pack(fill="x", padx=10, pady=5)
        
        self.btn_connect_host = ctk.CTkButton(self.frame_signaling, text="BAĞLANTIYI TAMAMLA", command=self.process_answer_host, fg_color=THEME["colors"]["success"])
        self.btn_connect_host.pack(pady=10)

        # Generate Offer Async
        self.run_async(self.generate_offer())

    async def generate_offer(self):
        self.pc = self.create_pc()
        
        # Create Data Channel
        self.channel = self.pc.createDataChannel("chat")
        self.setup_channel(self.channel)

        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Update UI threadsafe - Inject Identity for Manual Trusted Peer Logic
        local_ip = self.discovery._get_local_ip_and_broadcast()[0] if hasattr(self, 'discovery') else "0.0.0.0"
        offer_json = json.dumps({
            "sdp": self.pc.localDescription.sdp, 
            "type": self.pc.localDescription.type,
            "id": self.discovery.device_id,
            "user": self.discovery.username,
            "ip": local_ip
        })
        self.master.after(0, lambda: self.txt_offer.insert("0.0", offer_json))

    def process_answer_host(self):
        answer_str = self.txt_answer_input.get("0.0", "end").strip()
        if not answer_str:
            messagebox.showerror("Hata", "Lütfen karşı taraftan gelen cevabı yapıştırın.")
            return

        try:
            answer_data = json.loads(answer_str)
            self.run_async(self.set_remote_answer(answer_data))
            
            # Save as trusted peer if info exists
            if "id" in answer_data:
                self.save_trusted_peer(answer_data)
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"⭐ {answer_data.get('user', 'Peer')} güvenilir cihazlara eklendi!"))
                
        except Exception as e:
            messagebox.showerror("Hata", f"Geçersiz kod: {e}")

    async def set_remote_answer(self, data):
        answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        await self.pc.setRemoteDescription(answer)
        # Connection should establish automatically

    # --- JOIN MODE ---
    def show_join_mode(self):
        self.frame_signaling.pack(fill="both", expand=True, pady=10)
        
        for widget in self.frame_signaling.winfo_children():
            widget.destroy()

        self.pc = self.create_pc()
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self.channel = channel
            self.setup_channel(channel)

        ctk.CTkLabel(self.frame_signaling, text="KARŞIDAN GELEN KODU YAPIŞTIR (OFFER):", text_color="gray").pack(pady=5)
        entry_offer = ctk.CTkEntry(self.frame_signaling, width=400)
        entry_offer.pack(pady=5)
        
        def process_offer_and_generate_answer():
            offer_str = entry_offer.get()
            try:
                offer_json = json.loads(offer_str)
                rd = RTCSessionDescription(sdp=offer_json["sdp"], type=offer_json["type"])
                
                # Save Host as Trusted
                if "id" in offer_json:
                    self.save_trusted_peer(offer_json)
                    self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"⭐ {offer_json.get('user', 'Host')} güvenilir cihazlara eklendi!"))
                
                async def generate():
                    await self.pc.setRemoteDescription(rd)
                    answer = await self.pc.createAnswer()
                    await self.pc.setLocalDescription(answer)
                    
                    local_ip = self.discovery._get_local_ip_and_broadcast()[0] if hasattr(self, 'discovery') else "0.0.0.0"
                    ans_data = json.dumps({
                        "sdp": self.pc.localDescription.sdp, 
                        "type": self.pc.localDescription.type,
                        "id": self.discovery.device_id,
                        "user": self.discovery.username,
                        "ip": local_ip
                    })
                    
                    ctk.CTkLabel(self.frame_signaling, text="BU CEVABI KARŞIYA GÖNDER:", text_color="gray").pack(pady=(20, 5))
                    entry_ans = ctk.CTkEntry(self.frame_signaling, width=400)
                    entry_ans.pack(pady=5)
                    entry_ans.insert(0, ans_data)
                    
                self.run_async(generate())
            except Exception as e:
                messagebox.showerror("Hata", f"Geçersiz kod: {e}")
            
        ctk.CTkButton(self.frame_signaling, text="KODU OLUŞTUR (ANSWER)", command=process_offer_and_generate_answer).pack(pady=10)

    def process_offer_join(self):
        offer_str = self.txt_offer_input.get("0.0", "end").strip()
        if not offer_str:
            messagebox.showerror("Hata", "Lütfen offer kodunu yapıştırın.")
            return
        
        try:
            offer_data = json.loads(offer_str)
            self.run_async(self.generate_answer(offer_data))
        except Exception as e:
            messagebox.showerror("Hata", f"Geçersiz kod: {e}")

    async def generate_answer(self, offer_data):
        self.pc = self.create_pc()
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            print(f"[AETHER DEBUG] DataChannel event triggered on JOINER! Channel: {channel}")
            self.channel = channel
            self.setup_channel(channel)

        offer = RTCSessionDescription(sdp=offer_data["sdp"], type=offer_data["type"])
        await self.pc.setRemoteDescription(offer)
        
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        
        answer_json = json.dumps({"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type})
        self.master.after(0, lambda: self.txt_answer_output.insert("0.0", answer_json))


    # --- CHAT & CHANNEL LOGIC ---
    def setup_channel(self, channel):
        print(f"[AETHER DEBUG] setup_channel called for channel: {channel} | State: {channel.readyState}")
        
        @channel.on("open")
        def on_open():
            print("[AETHER DEBUG] Channel OPEN event triggered!")
            try:
                self.master.after(0, self.enable_chat_ui)
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", "Bağlantı Kuruldu! 🟢"))
            except Exception as e:
                print(f"[AETHER ERROR] Failed to enable chat UI: {e}")

        @channel.on("message")
        def on_message(message):
            print(f"[AETHER DEBUG] Message received RAW: {message!r}")
            try:
                # Ensure message is string
                if isinstance(message, bytes):
                    message = message.decode('utf-8')
                
                print(f"[AETHER DEBUG] Processing message: {message}")
                self.master.after(0, lambda m=message: self.add_chat_message("Partner", m))
            except Exception as e:
                print(f"[AETHER ERROR] Failed to display message: {e}")
                import traceback
                traceback.print_exc()

        # Check if already open (Fix for Windows Joiner race condition)
        if channel.readyState == "open":
            print("[AETHER DEBUG] Channel is ALREADY open, triggering handler manually.")
            on_open()

    def enable_chat_ui(self):
        self.frame_signaling.pack_forget()
        self.frame_chat.pack(fill="both", expand=True)
        self.lbl_title.configure(text="AETHER: BAĞLI 🟢", text_color=THEME["colors"]["success"])

    def send_message(self, event=None):
        msg = self.entry_message.get().strip()
        if not msg:
            return
        
        if self.channel and self.channel.readyState == "open":
            print(f"[AETHER DEBUG] Sending message: {msg}")
            try:
                # CRITICAL FIX: Send on the event loop thread!
                self.loop.call_soon_threadsafe(self.channel.send, msg)
                
                self.add_chat_message("Me", msg)
                self.entry_message.delete(0, "end")
            except Exception as e:
                print(f"[AETHER ERROR] Send failed: {e}")
                self.add_chat_message("System", f"İletim hatası: {e} 🔴")
        else:
            print(f"[AETHER DEBUG] Send failed. Channel state: {self.channel.readyState if self.channel else 'None'}")
            self.add_chat_message("System", "Bağlantı hazır değil! 🔴")

    def add_chat_message(self, sender, msg):
        def _append():
            if not self.txt_chat_history.winfo_exists(): return
            try:
                self.txt_chat_history.configure(state="normal")
                self.txt_chat_history.insert("end", f"[{sender}]: {msg}\n")
                self.txt_chat_history.configure(state="disabled")
                self.txt_chat_history.see("end")
            except Exception as e:
                print(f"[UI ERROR] Chat update failed: {e}")

        self.master.after(0, _append)

    # --- AUTOMATION LOGIC ---
    def on_peer_found_callback(self, peer_info):
        """Called by discovery thread when new peer is found."""
        self.master.after(0, lambda: self.update_peer_list(peer_info))

    def update_peer_list(self, peer_info):
        if self.lbl_no_peers:
            self.lbl_no_peers.pack_forget()
            self.lbl_no_peers = None
            
        display_name = f"{peer_info['user']} ({peer_info['ip']})"
        if display_name in self.known_peers:
            return
            
        self.known_peers[display_name] = peer_info
        
        pid = peer_info.get("id")
        is_trusted = pid in self.trusted_peers and self.trusted_peers[pid].get("trusted", False)
        
        btn_text = f"✨ BAĞLAN (GÜVENİLİR): {display_name}" if is_trusted else f"🔗 BAĞLAN: {display_name}"
        btn_color = THEME["colors"]["success"] if is_trusted else THEME["colors"]["accent"]
        
        btn = ctk.CTkButton(self.scroll_peers, text=btn_text, 
                            command=lambda: self.start_auto_connection(peer_info),
                            fg_color=btn_color, text_color="black")
        btn.pack(fill="x", pady=2, padx=5)

    def start_auto_connection(self, peer_info):
        """User clicked 'Connect' on a peer."""
        self.frame_discovery.pack_forget()
        self.frame_trusted.pack_forget() # Also hide trusted if called from there
        self.frame_chat.pack(fill="both", expand=True) # Prepare UI
        self.add_chat_message("SYSTEM", f"Bağlanılıyor: {peer_info['user']} ({peer_info['ip']})...")
        
        # Async: Generate Offer -> Send via TCP -> Receive Answer -> Set Remote
        self.run_async(self.async_auto_connect(peer_info))

    async def async_auto_connect(self, peer_info):
        # Use lock to prevent race if both sides try to connect simultaneously
        acquired = self.connection_lock.acquire(blocking=False)
        if not acquired:
            print("[AETHER] Connection already in progress, ignoring new request")
            self.master.after(0, lambda: self.add_chat_message("SYSTEM", "Bağlantı zaten devam ediyor..."))
            return
        
        try:
            # 1. Generate Offer
            self.pc = self.create_pc()
            self.channel = self.pc.createDataChannel("chat")
            self.setup_channel(self.channel)
            
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            offer_json = {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type, "id": self.discovery.device_id}
            
            # 2. Exchange via TCP (Blocking IO in Thread)
            # We run this in a thread executor to avoid blocking the asyncio loop
            loop = asyncio.get_event_loop()
            answer_json = await loop.run_in_executor(None, 
                lambda: self.handshake.connect_and_exchange(peer_info['ip'], peer_info['port'], offer_json)
            )
            
            # 3. Process Answer
            answer = RTCSessionDescription(sdp=answer_json["sdp"], type=answer_json["type"])
            await self.pc.setRemoteDescription(answer)
            
        except Exception as e:
            err_msg = str(e)
            if "peer is busy" in err_msg.lower():
                print(f"[AETHER] Connection collision detected: {err_msg}")
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", "⚠️ Karşı taraf meşgul veya size bağlanıyor. Bekleyiniz..."))
            else:
                print(f"[AUTO-CONNECT ERROR] {e}")
                self.master.after(0, lambda: messagebox.showerror("Hata", f"Otomatik bağlantı başarısız: {e}"))
                self.master.after(0, self.cleanup_and_home)
        finally:
            self.connection_lock.release()

    def handle_incoming_offer_auto(self, offer_json):
        """Called by Handshake Server Thread when someone connects to us."""
        print("[AETHER AUTO] Incoming connection request received!")
        
        # Check trust?
        peer_id = offer_json.get("id")
        if peer_id and peer_id in self.trusted_peers:
            print(f"[AETHER AUTO] Trusted Peer Connecting: {self.trusted_peers[peer_id]['user']}")
            # We could auto-accept here without any prompt if we wanted 'silent accept'
        
        future = asyncio.run_coroutine_threadsafe(self.async_handle_incoming_offer(offer_json), self.loop)
        return future.result() # Blocks TCP thread until Answer is ready

    async def async_handle_incoming_offer(self, offer_json):
        # Use lock to prevent race condition if reconnecting
        acquired = self.connection_lock.acquire(blocking=False)
        if not acquired:
            print("[AETHER] Ignoring incoming offer - connection already in progress")
            return None
        
        try:
            # Update UI first
            self.master.after(0, lambda: self.prepare_ui_for_incoming_auto())
            
            # Close old connection if exists
            if self.pc:
                print("[AETHER] Closing old connection before accepting new one")
                try:
                    await self.pc.close()
                    await asyncio.sleep(0.3)
                except:
                    pass
            
            self.pc = self.create_pc()
            
            @self.pc.on("datachannel")
            def on_datachannel(channel):
                self.channel = channel
                self.setup_channel(channel)
                
            offer = RTCSessionDescription(sdp=offer_json["sdp"], type=offer_json["type"])
            await self.pc.setRemoteDescription(offer)
            
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            return {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type, "id": self.discovery.device_id}
        finally:
            self.connection_lock.release()

    def prepare_ui_for_incoming_auto(self):
        try:
            self.frame_home.pack_forget() # If on home
            self.frame_discovery.pack_forget() # If on discovery
            self.frame_manual.pack_forget()
            
            self.frame_chat.pack(fill="both", expand=True)
            self.lbl_title.configure(text="GELEN BAĞLANTI KABUL EDİLDİ 🚀", text_color=THEME["colors"]["success"])
            self.add_chat_message("SYSTEM", "Otomatik bağlantı isteği alındı...")
        except Exception as e:
             print(f"[UI ERROR] UI Transition failed: {e}")

    def cleanup(self):
        """Clean up WebRTC connection state for reconnection."""
        if self.pc:
            try:
                self.run_async(self.pc.close())
            except:
                pass
            self.pc = None
        
        # Reset channel state
        self.channel = None
        
        # Clear connection failure flag if exists
        if hasattr(self, 'connection_failed_notified'):
            del self.connection_failed_notified
        
        # DON'T stop discovery/handshake - we need them for reconnection!
        # Only stop them when the entire app is closing
        print("[AETHER] WebRTC connection cleaned up, ready for reconnection")
    
    def on_app_destroy(self, event):
        """Called when the app widget is destroyed - do full cleanup."""
        print("[AETHER] App destroying, cleaning up all resources...")
        
        # Close WebRTC
        if self.pc:
            try:
                self.run_async(self.pc.close())
            except:
                pass
        
        # Stop discovery and handshake servers
        try:
            if hasattr(self, 'discovery'):
                self.discovery.stop()
            if hasattr(self, 'handshake'):
                self.handshake.stop()
        except:
            pass
        
        # Stop event loop
        try:
            self.loop.stop()
        except:
            pass
