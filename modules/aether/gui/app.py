
import customtkinter as ctk
import asyncio
import threading
import json
import logging
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
        
        # Start AsyncIO Loop in a separate thread
        self.thread = threading.Thread(target=self.start_loop, daemon=True)
        self.thread.start()

        # GUI Setup
        self.setup_ui()

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        """Schedule an async task in the loop thread"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Main Container ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)

        # --- Header ---
        self.lbl_title = ctk.CTkLabel(self.main_container, text="AETHER P2P AĞI", font=("Roboto", 24, "bold"), text_color=THEME["colors"]["text_primary"])
        self.lbl_title.grid(row=0, column=0, pady=(0, 20))

        # --- Connection Mode Selection ---
        self.frame_modes = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frame_modes.grid(row=1, column=0, sticky="ew")
        self.frame_modes.grid_columnconfigure((0, 1), weight=1)

        self.btn_host = ctk.CTkButton(self.frame_modes, text="BAĞLANTI BAŞLAT (HOST)", command=self.show_host_mode,
                                      fg_color=THEME["colors"]["accent"], text_color="black", height=50, font=("Roboto", 14, "bold"))
        self.btn_host.grid(row=0, column=0, padx=10, sticky="ew")

        self.btn_join = ctk.CTkButton(self.frame_modes, text="BAĞLAN (JOIN)", command=self.show_join_mode,
                                      fg_color=THEME["colors"]["bg_card_hover"], border_width=1, border_color=THEME["colors"]["border"],
                                      height=50, font=("Roboto", 14, "bold"))
        self.btn_join.grid(row=0, column=1, padx=10, sticky="ew")

        # --- SIGNALING AREA (Hidden by default) ---
        self.frame_signaling = ctk.CTkFrame(self.main_container)
        self.frame_signaling.grid(row=2, column=0, sticky="nsew", pady=20)
        self.frame_signaling.grid_columnconfigure(0, weight=1)
        self.frame_signaling.grid_remove() # Hide initially

        # --- CHAT AREA (Hidden by default) ---
        self.frame_chat = ctk.CTkFrame(self.main_container)
        self.frame_chat.grid(row=3, column=0, sticky="nsew", pady=10)
        self.frame_chat.grid_columnconfigure(0, weight=1)
        self.frame_chat.grid_rowconfigure(0, weight=1)
        self.frame_chat.grid_remove()

        self.txt_chat_history = ctk.CTkTextbox(self.frame_chat, state="disabled")
        self.txt_chat_history.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.entry_message = ctk.CTkEntry(self.frame_chat, placeholder_text="Mesaj yazın...")
        self.entry_message.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_message.bind("<Return>", self.send_message)


    def create_pc(self):
        stun_servers = [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
            "stun:stun2.l.google.com:19302",
            "stun:stun.services.mozilla.com"
        ]
        config = RTCConfiguration(iceServers=[RTCIceServer(urls=url) for url in stun_servers])
        pc = RTCPeerConnection(configuration=config)
        
        @pc.on("connectionstatechange")
        def on_connectionstatechange():
            print(f"[AETHER DEBUG] Connection state: {pc.connectionState}")
            self.update_status(f"Bağlantı Durumu: {pc.connectionState}")

        @pc.on("iceconnectionstatechange")
        def on_iceconnectionstatechange():
            print(f"[AETHER DEBUG] ICE state: {pc.iceConnectionState}")
            self.update_status(f"ICE Durumu: {pc.iceConnectionState}")
            
        return pc

    def update_status(self, text):
        try:
            color = "yellow"
            if "connect" in text.lower():
                color = THEME["colors"]["success"]
            elif "fail" in text.lower() or "close" in text.lower():
                color = THEME["colors"]["danger"]
            elif "check" in text.lower():
                color = "orange"
                
            self.master.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))
        except:
            pass

    # --- HOST MODE ---
    def show_host_mode(self):
        self.frame_modes.grid_remove()
        self.frame_signaling.grid()
        
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
        
        # Update UI threadsafe
        offer_json = json.dumps({"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type})
        self.master.after(0, lambda: self.txt_offer.insert("0.0", offer_json))

    def process_answer_host(self):
        answer_str = self.txt_answer_input.get("0.0", "end").strip()
        if not answer_str:
            messagebox.showerror("Hata", "Lütfen karşı taraftan gelen cevabı yapıştırın.")
            return

        try:
            answer_data = json.loads(answer_str)
            self.run_async(self.set_remote_answer(answer_data))
        except Exception as e:
            messagebox.showerror("Hata", f"Geçersiz kod: {e}")

    async def set_remote_answer(self, data):
        answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        await self.pc.setRemoteDescription(answer)
        # Connection should establish automatically

    # --- JOIN MODE ---
    def show_join_mode(self):
        self.frame_modes.grid_remove()
        self.frame_signaling.grid()

        self.lbl_status = ctk.CTkLabel(self.frame_signaling, text="Durum: Bekleniyor...", font=("Roboto", 14, "bold"), text_color="yellow")
        self.lbl_status.pack(pady=(0, 10))
        
        self.lbl_step1_join = ctk.CTkLabel(self.frame_signaling, text="ADIM 1: Karşı Taraftan Gelen Kodu (Offer) Yapıştır")
        self.lbl_step1_join.pack(pady=5)

        self.txt_offer_input = ctk.CTkTextbox(self.frame_signaling, height=100)
        self.txt_offer_input.pack(fill="x", padx=10, pady=5)

        self.btn_gen_answer = ctk.CTkButton(self.frame_signaling, text="CEVAP KODU ÜRET", command=self.process_offer_join, fg_color=THEME["colors"]["accent"], text_color="black")
        self.btn_gen_answer.pack(pady=10)

        self.lbl_step2_join = ctk.CTkLabel(self.frame_signaling, text="ADIM 2: Bu Kodu Kopyala ve Karşı Tarafa Gönder")
        self.lbl_step2_join.pack(pady=5)

        self.txt_answer_output = ctk.CTkTextbox(self.frame_signaling, height=100)
        self.txt_answer_output.pack(fill="x", padx=10, pady=5)

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
            print(f"[AETHER DEBUG] Message received: {message}")
            try:
                self.master.after(0, lambda m=message: self.add_chat_message("Partner", m))
            except Exception as e:
                print(f"[AETHER ERROR] Failed to display message: {e}")

        # Check if already open (Fix for Windows Joiner race condition)
        if channel.readyState == "open":
            print("[AETHER DEBUG] Channel is ALREADY open, triggering handler manually.")
            on_open()

    def enable_chat_ui(self):
        self.frame_signaling.grid_remove()
        self.frame_chat.grid()
        self.lbl_title.configure(text="AETHER: BAĞLI 🟢", text_color=THEME["colors"]["success"])

    def send_message(self, event=None):
        msg = self.entry_message.get().strip()
        if not msg:
            return
        
        if self.channel and self.channel.readyState == "open":
            self.channel.send(msg)
            self.add_chat_message("Me", msg)
            self.entry_message.delete(0, "end")
        else:
            self.add_chat_message("System", "Bağlantı hazır değil! 🔴")

    def add_chat_message(self, sender, msg):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", f"[{sender}]: {msg}\n")
        self.txt_chat_history.configure(state="disabled")
        self.txt_chat_history.see("end")

    def cleanup(self):
        if self.pc:
            self.run_async(self.pc.close())
        self.loop.stop()
