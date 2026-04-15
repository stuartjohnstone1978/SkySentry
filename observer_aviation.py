import os
import time
import requests
import ollama
import sys
import re
from dotenv import load_dotenv
from math import cos, asin, sqrt
from datetime import datetime 

# Load settings from .env file
load_dotenv()

# --- CONFIGURATION ---
HOME_LAT = float(os.getenv('HOME_LAT', 52.859))
HOME_LON = float(os.getenv('HOME_LON', -1.652))
RADIUS_KM = float(os.getenv('INTERCEPT_RADIUS', 15.0))

HOST_IP = os.getenv('HOST_IP', 'host.docker.internal')
MOUTH_PORT = os.getenv('MOUTH_PORT', '5001')
SHARED_SECRET = os.getenv('SHARED_SECRET', '')

MODEL = os.getenv('OLLAMA_MODEL', 'gemma4:e2b')

# --- GLOBAL STATE ---
seen_hexes = {}

def is_quiet_hour():
    """Checks if the current hour is within the defined quiet period."""
    start = int(os.getenv('QUIET_START', 23))
    end = int(os.getenv('QUIET_END', 7))
    current_hour = datetime.now().hour

    if start > end:  # Handles overnight (e.g., 23:00 to 07:00)
        return current_hour >= start or current_hour < end
    return start <= current_hour < end  # Handles daytime quiet hours

def get_coords_from_postcode(postcode):
    """Fetches Lat/Lon for a UK postcode using the free Postcodes.io API"""
    url = f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '')}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json().get('result', {})
            return data.get('latitude'), data.get('longitude')
        print(f"[Postcode Error] Could not find {postcode}")
    except Exception as e:
        print(f"[Postcode Error] API unreachable: {e}")
    return None, None

POSTCODE = os.getenv('POSTCODE')
if POSTCODE:
    lat, lon = get_coords_from_postcode(POSTCODE)
    if lat and lon:
        HOME_LAT, HOME_LON = lat, lon
        print(f"[Config] Calibration Complete: Using {POSTCODE} ({HOME_LAT}, {HOME_LON})")
    else:
        print(f"[Config] Postcode {POSTCODE} failed. Using manual fallback.")

def log(msg):
    print(f"[DEBUG] {msg}"); sys.stdout.flush()

def get_distance(lat2, lon2):
    """Haversine formula to calculate real-world distance in km"""
    p = 0.017453292519943295  # Pi/180
    a = 0.5 - cos((lat2 - HOME_LAT) * p)/2 + \
        cos(HOME_LAT * p) * cos(lat2 * p) * \
        (1 - cos((lon2 - HOME_LON) * p)) / 2
    return 12742 * asin(sqrt(a))

def get_military_planes():
    """Fetches military aircraft data from adsb.lol"""
    url = "https://api.adsb.lol/v2/mil/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Sentry/1.0',
        'Accept': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get('ac', [])
        return []
    except Exception as e:
        print(f"[Network Error] {e}")
        return []

def get_ai_announcement(type_code, callsign, weather_context):
    """Generates a friendly alert using the local Gemma model"""
    # Sanitize inputs to prevent LLM prompt injection
    safe_type = re.sub(r'[^a-zA-Z0-9-]', '', str(type_code))[:15]
    safe_callsign = re.sub(r'[^a-zA-Z0-9]', '', str(callsign))[:10]

    # Prompt is now location-agnostic
    prompt = (
        f"You are a friendly aviation enthusiast. A {safe_type} aircraft with "
        f"callsign {safe_callsign} is flying in the local area. "
        f"Context: {weather_context} "
        f"Write a 10-word alert"
    )
    try:
        response = ollama.chat(model=MODEL, messages=[
            {'role': 'user', 'content': prompt}
        ])
        return response['message']['content'].strip()
    except Exception as e:
        print(f"[Ollama Error] {e}")
        return f"Look up! A {safe_type} ({safe_callsign}) is passing by!"

def speak(text):
    """Forwards the alert to the Windows Mouth bridge with auth header"""
    url = f"http://{HOST_IP}:{MOUTH_PORT}/say"
    headers = {'X-Sentry-Auth': SHARED_SECRET}
    payload = {"text": text}
    
    try:
        print(f"Forwarding to Mouth: {text}")
        requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"[Bridge Error] Could not reach Mouth: {e}")

def get_weather_context():
    try:
        # Talks to the Weather Agent on Port 5002
        r = requests.get("http://host.docker.internal:5002/status")
        return r.json()
    except:
        return {"cloud_pct": 50, "rain_now": 0}

def run_sentry():
    global seen_hexes
    log(f"SkySentry Active. Monitoring {RADIUS_KM}km around {HOME_LAT}, {HOME_LON}")
    
    while True:
        planes = get_military_planes()
        current_time = time.time()  # <--- FIX: Define current_time at the start of each pulse
        
        for p in planes:
            icao_hex = p.get('hex')
            lat, lon = p.get('lat'), p.get('lon')
            
            if icao_hex and lat and lon:
                dist = get_distance(lat, lon)
                
                # Logic for return flights
                last_seen = seen_hexes.get(icao_hex, 0)
                is_fresh_sighting = (current_time - last_seen) > 3600 # 1 hour
                
                # UPDATED: Use is_fresh_sighting instead of 'not in seen_hexes'
                if dist <= RADIUS_KM and is_fresh_sighting:
                    type_code = p.get('t', 'Military Aircraft')
                    callsign = p.get('flight', 'Unknown').strip()
                    
                    log(f"!!! INTERCEPT: {type_code} ({callsign}) at {dist:.1f}km !!!")

                    weather = get_weather_context()
                    cloud_pct = weather.get('cloud_pct', 0)
                    is_cloudy = cloud_pct > 80
                    
                    weather_context = "Cloudy skies." if is_cloudy else "Clear skies."

                    if is_quiet_hour():
                        log(f"Suppressed {callsign} (Quiet Hours).")
                    elif is_cloudy and type_code not in ['TYPH', 'F35', 'R1', 'VULC', 'LANC', 'EUFI']:
                        log(f"Suppressed {callsign} (Low visibility).")
                    else:
                        alert_msg = get_ai_announcement(type_code, callsign, weather_context)
                        speak(alert_msg)

                    # Update the dictionary with the current timestamp
                    seen_hexes[icao_hex] = current_time

        # Housekeeping: Cleanup old entries every pulse to keep memory lean
        cutoff = current_time - 7200 # 2 hours
        seen_hexes = {hex_id: ts for hex_id, ts in seen_hexes.items() if ts > cutoff}
                    
        time.sleep(45)
if __name__ == "__main__":
    run_sentry()