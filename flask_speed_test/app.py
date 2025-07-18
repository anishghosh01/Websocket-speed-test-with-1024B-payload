from flask import Flask, render_template
from flask_socketio import SocketIO
import time
import asyncio
import websockets
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration
ESP32_IP = "192.168.0.232"  # Replace with your ESP32 IP
PORT = 81                   # Replace with your WebSocket port
URI = f"ws://{ESP32_IP}:{PORT}/ws"
PAYLOAD_SIZE = 1024  # 1 KB test packet
PAYLOAD = "X" * PAYLOAD_SIZE
SEND_INTERVAL = 0.005  # seconds (200 packets/sec)

# Global variables for speed tracking
tx_speed = 0
rx_speed = 0
running = False

def speed_monitor():
    global tx_speed, rx_speed, running
    
    async def speed_test():
        global tx_speed, rx_speed
        try:
            async with websockets.connect(URI, ping_interval=None) as ws:
                print(f"Connected to {URI}")
                sent = recv = 0
                t0 = time.time()

                while running:
                    await ws.send(PAYLOAD)
                    sent += len(PAYLOAD)

                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1)
                        recv += len(msg)
                    except asyncio.TimeoutError:
                        print("Timeout: No echo received")

                    if time.time() - t0 >= 1.0:
                        tx_speed = sent * 8 / 1000  # Convert to kbps
                        rx_speed = recv * 8 / 1000  # Convert to kbps
                        socketio.emit('speed_update', {
                            'tx_speed': round(tx_speed, 1),
                            'rx_speed': round(rx_speed, 1)
                        })
                        t0 = time.time()
                        sent = recv = 0

                    await asyncio.sleep(SEND_INTERVAL)

        except Exception as e:
            print(f"Connection error: {e}")
            socketio.emit('speed_update', {
                'tx_speed': 0,
                'rx_speed': 0
            })
    
    asyncio.run(speed_test())

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global running
    print("🔗 Browser connected")
    if not running:
        running = True
        Thread(target=speed_monitor, daemon=True).start()

@socketio.on('disconnect')
def handle_disconnect():
    global running
    print("❌ Browser disconnected")
    running = False

if __name__ == '__main__':
    socketio.run(app, debug=True)