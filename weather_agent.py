import os
import requests
from flask import Flask, jsonify
from waitress import serve
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = "Rolleston-on-Dove"
# Cache to avoid hammering the API
cache = {"data": None, "timestamp": 0}

def fetch_weather():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={API_KEY}&units=metric"
    # We use 'forecast' to see the next few hours for your washing machine!
    response = requests.get(url).json()
    return response

@app.route('/status')
def status():
    # Logic to return current cloud cover and 3-hour rain probability
    data = fetch_weather()
    current = data['list'][0]
    upcoming = data['list'][1] # Next 3 hours
    
    return jsonify({
        "cloud_pct": current['clouds']['all'],
        "rain_now": current.get('rain', {}).get('3h', 0),
        "rain_soon": upcoming.get('rain', {}).get('3h', 0),
        "temp": current['main']['temp']
    })

if __name__ == '__main__':
    print("Weather Agent Active: Monitoring the clouds over Rolleston...")
    serve(app, host='0.0.0.0', port=5002)