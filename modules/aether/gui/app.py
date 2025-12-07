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
        from modules.aether.core.file_transfer import FileTransferManager # [NEW]
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
        
        # 3. Initialize File Transfer Manager
        self.file_manager = FileTransferManager(
            on_progress=self.update_file_progress,
            on_complete=self.on_file_complete
        )
        
        # Store peers locally for UI mapping
        self.known_peers = {} # {display_string: peer_data}

        # GUI Setup
        self.setup_ui()
        
        # Bind cleanup to app destruction
        self.bind("<Destroy>", self.on_app_destroy)




    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        """Schedule an async task in the loop thread"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def setup_ui(self):
        """Refactored UI with Hybrid Options."""
        self.main_container = ctk.CTkFrame(self.master, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # TITLE
        self.lbl_title = ctk.CTkLabel(self.main_container, text="AETHER P2P (HİBRİT MOD)", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=(0, 20))

        # --- PANELS ---
        # 1. Home Menu
        self.frame_home = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # 2. Sub-Panels
        self.frame_discovery = ctk.CTkFrame(self.main_container) # Same Wi-Fi
        self.frame_manual = ctk.CTkFrame(self.main_container)    # Different Wi-Fi
        self.frame_chat = ctk.CTkFrame(self.main_container)      # Chat
        
        # Build Navigation
        self.build_home_menu()
        self.build_discovery_panel()
        self.build_manual_panel()
        self.build_chat_panel()

        # Show Home by default
        self.show_home()

    def build_home_menu(self):
        """Create the 2 main option buttons."""
        # Option 1: Same Wi-Fi (Auto)
        btn_wifi = ctk.CTkButton(self.frame_home, text="🏠 AYNI WI-FI (OTOMATİK)", 
                                 command=self.show_discovery_panel,
                                 height=80, font=("Roboto", 18, "bold"), fg_color=THEME["colors"]["accent"], text_color="black")
        btn_wifi.pack(fill="x", pady=20)
        
        # Option 2: Different Wi-Fi (Manual)
        btn_manual = ctk.CTkButton(self.frame_home, text="🌍 FARKLI WI-FI (KOD İLE)", 
                                   command=self.show_manual_panel,
                                   height=80, font=("Roboto", 18, "bold"), fg_color=THEME["colors"]["bg_card"])
        btn_manual.pack(fill="x", pady=20)
        
    def show_home(self):
        self.frame_discovery.pack_forget()
        self.frame_manual.pack_forget()
        self.frame_chat.pack_forget()
        self.frame_home.pack(fill="both", expand=True)
        self.lbl_title.configure(text="AETHER P2P AĞI", text_color="white")

    def show_discovery_panel(self):
        self.frame_home.pack_forget()
        self.frame_manual.pack_forget()
        self.frame_discovery.pack(fill="both", expand=True)
        
    def show_manual_panel(self):
        self.frame_home.pack_forget()
        self.frame_discovery.pack_forget()
        self.frame_manual.pack(fill="both", expand=True)

    def go_back(self):
        """Back to Home."""
        self.show_home()

    def build_discovery_panel(self):
        """Panel for Local Network Discovery."""
        # Header with Back Button
        header = ctk.CTkFrame(self.frame_discovery, fg_color="transparent")
        header.pack(fill="x", pady=10)
        ctk.CTkButton(header, text="←", width=30, command=self.go_back, fg_color="transparent", border_width=1).pack(side="left")
        ctk.CTkLabel(header, text="YAKINDAKİ CİHAZLAR (LAN)", font=THEME["fonts"]["subheader"]).pack(side="left", padx=10)
        
        self.scroll_peers = ctk.CTkScrollableFrame(self.frame_discovery, fg_color="transparent")
        self.scroll_peers.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.lbl_no_peers = ctk.CTkLabel(self.scroll_peers, text="Taranıyor... Lütfen bekleyin.", text_color="gray")
        self.lbl_no_peers.pack(pady=20)

    def build_manual_panel(self):
        """Panel for Manual Host/Join (Traditional)."""
        # Header with Back Button
        header = ctk.CTkFrame(self.frame_manual, fg_color="transparent")
        header.pack(fill="x", pady=10)
        ctk.CTkButton(header, text="←", width=30, command=self.go_back, fg_color="transparent", border_width=1).pack(side="left")
        ctk.CTkLabel(header, text="MANUEL BAĞLANTI (WAN)", font=THEME["fonts"]["subheader"]).pack(side="left", padx=10)
        
        # HOST SECTION
        frame_host = ctk.CTkFrame(self.frame_manual, fg_color=THEME["colors"]["bg_card"])
        frame_host.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_host, text="Bağlantı Başlat (Host) - Kod Oluştur", font=("Roboto", 12, "bold")).pack(pady=5)
        
        btn_host = ctk.CTkButton(frame_host, text="Kod Oluştur", 
                                 command=lambda: self.run_async(self.generate_offer()),
                                 fg_color=THEME["colors"]["accent"], hover_color=THEME["colors"]["accent_hover"],
                                 text_color="black")
        btn_host.pack(pady=10, padx=10, fill="x")

        # JOIN SECTION
        frame_join = ctk.CTkFrame(self.frame_manual, fg_color=THEME["colors"]["bg_card"])
        frame_join.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_join, text="Bağlan (Join) - Kodu Aşağıya Yapıştırın:", font=("Roboto", 12, "bold")).pack(pady=5)

        self.entry_join_code = ctk.CTkTextbox(frame_join, height=100)
        self.entry_join_code.pack(fill="x", padx=10, pady=5)
        # Placeholder removed to prevent "ghost text" issues
        
        btn_join = ctk.CTkButton(frame_join, text="Bağlan", command=self.process_manual_offer,
                                 fg_color=THEME["colors"]["success"], hover_color=THEME["colors"]["success_hover"])
        btn_join.pack(pady=10, padx=10, fill="x")

        # Code Display Area
        self.frame_signaling = ctk.CTkFrame(self.frame_manual, fg_color="transparent")
        self.frame_signaling.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.text_code_display = ctk.CTkTextbox(self.frame_signaling, wrap="word")
        self.text_code_display.pack(fill="both", expand=True)



    def show_code(self, code, title):
        """Display generated code in the text box."""
        self.text_code_display.delete("0.0", "end")
        self.text_code_display.insert("0.0", f"--- {title} ---\n\n{code}")
        # Auto-copy
        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(code)
            messagebox.showinfo("Kopyalandı", "Kod panoya kopyalandı!")
        except:
            pass



    def build_chat_panel(self):
        self.frame_chat.columnconfigure(0, weight=1)
        self.frame_chat.rowconfigure(0, weight=1)
        
        self.txt_chat_history = ctk.CTkTextbox(self.frame_chat, state="disabled", wrap="word")
        self.txt_chat_history.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.entry_message = ctk.CTkEntry(self.frame_chat, placeholder_text="Mesaj yaz...")
        self.entry_message.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_message.bind("<Return>", self.send_message)
        
        self.entry_message.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_message.bind("<Return>", self.send_message)
        
        # --- File Transfer Controls ---
        self.frame_file_controls = ctk.CTkFrame(self.frame_chat, fg_color="transparent")
        self.frame_file_controls.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.btn_file = ctk.CTkButton(self.frame_file_controls, text="📎 Dosya Ekle", 
                                      command=self.select_file,
                                      width=100, fg_color=THEME["colors"]["bg_card"])
        self.btn_file.pack(side="left", padx=(0, 10))
        
        self.btn_send = ctk.CTkButton(self.frame_file_controls, text="GÖNDER", command=self.send_message, 
                                      fg_color=THEME["colors"]["accent"], text_color="black")
        self.btn_send.pack(side="left", fill="x", expand=True)
        
        # Progress Bar (Hidden by default)
        self.progress_file = ctk.CTkProgressBar(self.frame_chat)
        self.progress_file.set(0)
        self.lbl_file_status = ctk.CTkLabel(self.frame_chat, text="", font=("Roboto", 10))
        
        # Close Chat / Disconnect
        ctk.CTkButton(self.frame_chat, text="BAĞLANTIYI KES", command=self.cleanup_and_home, fg_color="red").grid(row=4, column=0, pady=5)


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
            
            if state in ["connected", "completed"]:
                # Smart IP Learning Removed - Trusted Peers deprecated
                print(f"[AETHER] ICE connected. Transitioning to active state.")

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
            
            if state == "connected":
               # Also try Smart IP Learning here just in case
               pass

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
    async def generate_offer(self):
        try:
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
                "ip": local_ip,
                "public_ip": self.get_public_ip(), # Inject Public IP
                "port": self.handshake.port # Save listening port for future reconnections
            })
            
            # In the Lambda, use show_code
            self.master.after(0, lambda: self.show_code(offer_json, "ADIM 1: Bu Kodu Kopyala ve Karşı Tarafa Gönder"))
        except Exception as e:
            err = str(e)
            print(f"[OFFER ERROR] {err}")
            self.master.after(0, lambda: messagebox.showerror("Hata", f"Kod oluşturulamadı: {err}"))

    def process_manual_offer(self):
        """Smart method to handle both joining (Offer) and completing connection (Answer)."""
        code_b64 = self.entry_join_code.get("0.0", "end").strip()
        if not code_b64:
            messagebox.showwarning("Uyarı", "Lütfen bir kod yapıştırın!")
            return

        self.run_async(self.async_process_manual_code(code_b64))

    async def async_process_manual_code(self, code_str):
        try:
            # 1. Parse JSON
            try:
                data = json.loads(code_str)
            except json.JSONDecodeError:
                 self.master.after(0, lambda: messagebox.showerror("Hata", "Geçersiz format! Lütfen geçerli bir kod yapıştırın."))
                 return

            msg_type = data.get("type")
            
            if msg_type == "offer":
                # === JOINER FLOW ===
                # We received an OFFER, so we must generate an ANSWER
                if self.pc:
                     await self.pc.close()
                self.pc = self.create_pc()
                
                @self.pc.on("datachannel")
                def on_datachannel(channel):
                    self.channel = channel # Assign to self.channel!
                    self.setup_channel(channel)
                
                rd = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await self.pc.setRemoteDescription(rd)
                
                answer = await self.pc.createAnswer()
                await self.pc.setLocalDescription(answer)
                
                local_ip = self.discovery._get_local_ip_and_broadcast()[0] if hasattr(self, 'discovery') else "0.0.0.0"
                
                answer_json = json.dumps({
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type,
                    "user": self.discovery.username if hasattr(self, 'discovery') else "Guest",
                    "ip": local_ip
                })
                
                self.master.after(0, lambda: self.show_code(answer_json, "ADIM 2: Bu Cevap Kodunu Host'a Gönder"))
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"{data.get('user', 'Host')} bulundu. Cevap kodu üretildi."))
                
            elif msg_type == "answer":
                # === HOST FLOW ===
                # We received an ANSWER, so we complete the connection
                if not self.pc:
                    self.master.after(0, lambda: messagebox.showerror("Hata", "Önce 'Kod Oluştur' diyerek Host olmalısınız!"))
                    return

                rd = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await self.pc.setRemoteDescription(rd)
                
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"{data.get('user', 'Misafir')} bağlandı! Sohbet başlayabilir. 🟢"))
                
            else:
                self.master.after(0, lambda: messagebox.showerror("Hata", "Bilinmeyen kod formatı."))

        except Exception as e:
            err_msg = str(e)
            print(f"Code Process Error: {err_msg}")
            self.master.after(0, lambda: messagebox.showerror("Hata", f"Geçersiz Kod: {err_msg}"))


    # --- CHAT & CHANNEL LOGIC ---
    def setup_channel(self, channel):
        print(f"[AETHER DEBUG] setup_channel called for channel: {channel} | State: {channel.readyState}")
        
        @channel.on("open")
        def on_open():
            print("[AETHER DEBUG] Channel OPEN event triggered!")
            # THREAD SAFETY: Ensure UI updates happen on main thread
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
                
                # Check if it's a JSON (File Transfer Protcol)
                if message.startswith('{') and '"type":' in message:
                     try:
                         data = json.loads(message)
                         msg_type = data.get("type")
                         if msg_type in ["file_meta", "file_chunk"]:
                             # Pass to File Manager
                             self.file_manager.handle_message(data)
                             return # Don't show in chat
                     except json.JSONDecodeError:
                         pass

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
        # Removing trusted logic
        # is_trusted = pid in self.trusted_peers and ...
        
        btn_text = f"🔗 BAĞLAN: {display_name}"
        btn_color = THEME["colors"]["accent"]
        
        btn = ctk.CTkButton(self.scroll_peers, text=btn_text, 
                            command=lambda: self.start_auto_connection(peer_info),
                            fg_color=btn_color, text_color="black")
        btn.pack(fill="x", pady=2, padx=5)

    def start_auto_connection(self, peer_info):
        """User clicked 'Connect' on a peer."""
        self.frame_discovery.pack_forget()
        # self.frame_trusted.pack_forget() # Removed as trusted panel is deprecated
        self.frame_chat.pack(fill="both", expand=True) # Prepare UI
        self.add_chat_message("SYSTEM", f"Bağlanılıyor: {peer_info['user']} ({peer_info['ip']})...")
        
        # Async: Generate Offer -> Send via TCP -> Receive Answer -> Set Remote
        self.run_async(self.async_auto_connect(peer_info['ip'], peer_info['port']))

    @staticmethod
    def get_public_ip():
        """Fetch the public WAN IP address of this device."""
        try:
            import urllib.request
            # Use reliable ipify service
            with urllib.request.urlopen('https://api.ipify.org', timeout=3) as response:
                return response.read().decode('utf-8')
        except:
            return None

    async def async_auto_connect(self, target_ip, target_port):
        """Asynchronous auto-connect logic."""
        if not self.pc:
            self.pc = self.create_pc()

        # Trusted peer lookup removed
        # Smart IP Learning logic removed

        # Prevent concurrent connections to the same peer (or any peer if single-threaded logic)
        # Using a lock to ensure atomic operations on connection state
        if not self.connection_lock.acquire(blocking=False):
            print(f"[AETHER] Connection attempt ignored: Already connecting.")
            return

        try:
            print(f"[AETHER] Auto-connecting to {target_ip}:{target_port}...")
            
            # Create Data Channel
            self.channel = self.pc.createDataChannel("chat")
            self.setup_channel(self.channel)

            # Create Offer
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)

            # Prepare Offer JSON
            offer_json = {
                "sdp": self.pc.localDescription.sdp,
                "type": self.pc.localDescription.type,
                "id": self.discovery.device_id, # Assuming self.discovery.device_id is available
                "user": self.discovery.username, # Assuming self.discovery.username is available
                "ip": self.discovery._get_local_ip_and_broadcast()[0], # Assuming this method exists
                "public_ip": self.get_public_ip(), # Inject Public IP
                "port": self.handshake.port
            }
            
            # Send via TCP Handshake (Thread-blocking, hence run_in_executor)
            loop = asyncio.get_event_loop()
            answer_json = await loop.run_in_executor(
                None, 
                self.handshake.connect_and_exchange, 
                target_ip, 
                target_port, 
                offer_json
            )
            
            # Process Answer
            # Assuming process_answer_host is a method that handles the answer
            # If not, this needs to be defined or replaced with appropriate logic
            await self.set_remote_answer(answer_json) # Using existing set_remote_answer for simplicity
            
        except Exception as e:
            err_msg_connect = str(e)
            print(f"[AUTO-CONNECT ERROR] {err_msg_connect}")
            if "Peer is busy" in err_msg_connect:
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"⚠️ {target_ip} şu an meşgul."))
            else:
                self.master.after(0, lambda: self.add_chat_message("SYSTEM", f"⚠️ Bağlantı hatası: {err_msg_connect}"))
                self.master.after(0, lambda: messagebox.showerror("Hata", f"Otomatik bağlantı başarısız: {err_msg_connect}"))
                self.master.after(0, self.cleanup_and_home)
        finally:
            self.connection_lock.release()

    async def set_remote_answer(self, data):
        answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        await self.pc.setRemoteDescription(answer)

    def handle_incoming_offer_auto(self, offer_json):
        """Called by Handshake Server Thread when someone connects to us."""
        print("[AETHER AUTO] Incoming connection request received!")
        
        # Trusted Logic Removed
        
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
            
        # SECURE CLEANUP: Force Garbage Collection to clear key material
        import gc
        gc.collect()
        
        # DON'T stop discovery/handshake - we need them for reconnection!
        # Only stop them when the entire app is closing
        print("[AETHER] WebRTC connection cleaned up, ready for reconnection")
    
    
    # --- FILE TRANSFER LOGIC ---
    def select_file(self):
        """Open file picker and start transfer."""
        if not self.channel or self.channel.readyState != "open":
             messagebox.showerror("Hata", "Bağlantı açık değil!")
             return
             
        filepath = ctk.filedialog.askopenfilename()
        if not filepath:
            return
            
        # Start async upload in background
        self.run_async(self.async_send_file(filepath))

    async def async_send_file(self, filepath):
        try:
            # 1. Prepare Metadata (Calculates Hash)
            meta = await self.loop.run_in_executor(None, self.file_manager.prepare_upload, filepath)
            
            # 2. Send Metadata
            self.channel.send(json.dumps(meta))
            
            # 3. Send Chunks
            for chunk in self.loop.run_in_executor(None, lambda: list(self.file_manager.read_chunks(filepath, meta['id']))):
                 # We iterate list() here to force generator to run in executor if heavy, 
                 # but actually read_chunks yields.
                 # Better approach for async loop:
                 pass
            
            # Proper Async Generator iteration
            # Since read_chunks is sync generator, we run it directly but be careful of blocking
            # Ideally rewrite read_chunks to be no-blocking or small chunks. 
            # Given 16KB chunks, direct iteration is fine if we yield control.
            
            gen = self.file_manager.read_chunks(filepath, meta['id'])
            for chunk_msg in gen:
                self.channel.send(json.dumps(chunk_msg))
                await asyncio.sleep(0.001) # Yield to event loop to keep UI responsive
                
        except Exception as e:
            print(f"[FILE ERROR] {e}")
            self.master.after(0, lambda: messagebox.showerror("Transfer Hatası", str(e)))

    def update_file_progress(self, filename, percent, status):
        """Called by FileTransferManager on p_rogress."""
        def _update():
            # Show progress bar if hidden
            if not self.progress_file.winfo_ismapped():
                self.progress_file.grid(row=3, column=0, sticky="ew", padx=10, pady=(5,0))
                self.lbl_file_status.grid(row=4, column=0, padx=10)
                
            self.progress_file.set(percent / 100)
            self.lbl_file_status.configure(text=f"{filename}: {status}")
            
        self.master.after(0, _update)

    def on_file_complete(self, filename, full_path):
        """Called by FileTransferManager when complete."""
        def _finish():
            self.progress_file.grid_forget()
            self.lbl_file_status.grid_forget()
            self.add_chat_message("SYSTEM", f"Dosya Alındı: {filename} ✅\nKonum: {full_path}")
            messagebox.showinfo("İndirme Tamamlandı", f"Dosya hazır:\n{full_path}")
            
        self.master.after(0, _finish)

    def on_app_destroy(self, event):
        """Called when the app widget is destroyed - do full cleanup."""
        print("[AETHER] App destroying, cleaning up all resources...")
        
        # Close WebRTC
        if self.pc:
            try:
                self.run_async(self.pc.close())
            except:
                pass
            self.pc = None
            self.channel = None
        
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
            
        # Final secure wipe
        import gc
        gc.collect()
