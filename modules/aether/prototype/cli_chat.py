
import argparse
import asyncio
import json
import logging
import sys

# Monkey Patch for av <-> aiortc compatibility (Python 3.13 / av 13.0.0)
try:
    import av
    if not hasattr(av, 'AudioCodecContext') and hasattr(av, 'CodecContext'):
        av.AudioCodecContext = av.CodecContext
except ImportError:
    pass

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel, RTCConfiguration, RTCIceServer

# Configure logging
logging.basicConfig(level=logging.ERROR) # Only errors to keep CLI clean

async def run_chat(pc, signaling_role):
    # Channel handling logic
    channel = None

    def log_msg(msg):
        print(f"\n[AETHER] {msg}")

    if signaling_role == "host":
        log_msg("Creating Data Channel 'chat'...")
        channel = pc.createDataChannel("chat")
        
        @channel.on("open")
        def on_open():
            log_msg("Channel OPEN! You can start typing messages.")
            log_msg("Type 'quit' to exit.")

        @channel.on("message")
        def on_message(message):
            print(f"\n> Peer: {message}")

    else: # joiner
        @pc.on("datachannel")
        def on_datachannel(chan):
            nonlocal channel
            channel = chan
            log_msg(f"Channel received: {channel.label}")
            
            @channel.on("message")
            def on_message(message):
                print(f"\n> Peer: {message}")
                
            @channel.on("open")
            def on_open():
                log_msg("Channel OPEN! Type messages.")

    # Signaling Exchange
    print("\n" + "="*40)
    print(f"ROLE: {signaling_role.upper()}")
    print("="*40)

    if signaling_role == "host":
        # Create Offer
        log_msg("Generating OFFER...")
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # Print Offer
        offer_json = json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
        print(f"\n--- COPY THIS OFFER TO THE OTHER PEER ---\n{offer_json}\n-----------------------------------------")

        # Wait for Answer
        answer_str = input("\n[PASTE ANSWER HERE]: ").strip()
        answer_data = json.loads(answer_str)
        answer = RTCSessionDescription(sdp=answer_data["sdp"], type=answer_data["type"])
        
        await pc.setRemoteDescription(answer)
        log_msg("Remote Description Set. Connection should establish...")

    else: # joiner
        # Wait for Offer
        offer_str = input("\n[PASTE OFFER HERE]: ").strip()
        offer_data = json.loads(offer_str)
        offer = RTCSessionDescription(sdp=offer_data["sdp"], type=offer_data["type"])
        
        await pc.setRemoteDescription(offer)
        
        # Create Answer
        log_msg("Generating ANSWER...")
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Print Answer
        answer_json = json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
        print(f"\n--- COPY THIS ANSWER TO THE HOST ---\n{answer_json}\n------------------------------------")

    # Chat Loop
    print("\n[Chat System Ready]")
    while True:
        # Simple blocking input for prototype (in GUI this will be event driven)
        # Using run_in_executor to not block the asyncio loop
        msg = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        msg = msg.strip()
        
        if msg == "quit":
            break
            
        if channel and channel.readyState == "open":
            channel.send(msg)
            # print(f"Me: {msg}") # Optional echo
        else:
            print("[System] Channel not ready yet...")
            
    # Cleanup
    await pc.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AETHER P2P Chat Prototype")
    parser.add_argument("role", choices=["host", "joiner"], help="Role: host (creates offer) or joiner (answers)")
    args = parser.parse_args()

    # STUN Server Configuration for NAT Traversal (Cross-Network P2P)
    config = RTCConfiguration(
        iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302")
        ]
    )
    
    pc = RTCPeerConnection(configuration=config)
    
    try:
        asyncio.run(run_chat(pc, args.role))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
