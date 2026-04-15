from flask import Flask, request, send_file
import pychromecast
from gtts import gTTS
import os, time, sys
import hmac
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Config from .env
NEST_IP = os.getenv('NEST_IP')
HOST_IP = os.getenv('HOST_IP')
PORT = int(os.getenv('MOUTH_PORT', 5001))
SECRET = os.getenv('SHARED_SECRET')
MP3_PATH = os.path.join(os.path.dirname(__file__), "alert.mp3")

def log(msg):
    clean_msg = msg.replace('\n', ' ').replace('\r', ' ')
    print(f"[DEBUG] {clean_msg}")

@app.route('/say', methods=['POST'])
def say():
    # Secure, constant-time authentication check
    provided_secret = request.headers.get('X-Sentry-Auth', '')
    if not hmac.compare_digest(provided_secret, SECRET):
        log("Unauthorized access attempt!")
        return "Forbidden", 403

    text = request.json.get('text', 'No text')
    
    # Input validation: Prevent DoS via massive text payloads
    if len(text) > 300:
        log("Payload too large rejected.")
        return "Payload Too Large", 413
        
    safe_log_text = text.replace('\n', ' ').replace('\r', '')
    log(f"Received: {safe_log_text}")
    
   # 1. TTS
    try:
        if os.path.exists(MP3_PATH): 
            os.remove(MP3_PATH)
    except PermissionError:
        log("File locked, skipping delete...") # Nest is likely still reading it
    
    gTTS(text=text, lang='en', tld='co.uk').save(MP3_PATH)

    # 2. Connect (Using the 'Surgical' Tuple fix for Python 3.13)
    try:
        cast = pychromecast.get_chromecast_from_host((NEST_IP, 8009, None, None, None))
        cast.wait()
        media_url = f"http://{HOST_IP}:{PORT}/listen?cb={int(time.time())}"
        cast.media_controller.play_media(media_url, "audio/mp3")
        cast.media_controller.block_until_active()
        return "OK", 200
    except Exception as e:
        log(f"Error: {e}"); return str(e), 500

@app.route('/listen')
def listen():
    return send_file(MP3_PATH, mimetype="audio/mp3")

if __name__ == '__main__':
    log(f"Mouth Active on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)