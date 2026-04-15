## 🛰️ SkySentry: AI-Powered Aviation Monitor
SkySentry is an autonomous system that monitors the skies for military aircraft. It combines real-time ADS-B telemetry with local Large Language Models (LLMs) to provide natural, spoken alerts via your smart home speakers.

## 🚀 How it Works
- **Detection**: The Brain (running in Docker) polls the adsb.lol API to track military transponders.
- **Calibration**: The system uses a UK Postcode or coordinates to establish your "Home Base."
- **Intelligence**: When an aircraft enters your designated radius (e.g., 15km), the telemetry is sent to a local Gemma model via Ollama.
- **Action**: Gemma generates a unique, enthusiast-style alert.
- **Broadcast**: This alert is sent to the Mouth (a Python bridge), which uses Text-to-Speech to broadcast the notification through your Google Nest or Chromecast device.

## 🛠️ Project Structure
```sentry.py```: The core logic engine (Python in Docker).

```mouth.py```: The hardware bridge (Python on Host OS).

```docker-compose.yml```: Orchestrates the Sentry and AI services.

```.env```: Your private configuration (Postcodes, IPs, and Secrets).

## ⚡ Quick Start
### 1. Prerequisites
Docker Desktop: Installed and running.
- Ollama: Installed and running (ensure the model specified in .env is pulled, e.g., ollama pull gemma4:e2b).
- Python 3.11+: Installed on your host machine (Windows or macOS).

### 2. Installation
- Clone this repository to your local machine.
- Copy .env.example to a new file named .env.
- Edit .env and provide your specific details (Postcode, Nest IP, and Shared Secret).

### 3. Launching the System
- Step A: Start the Brain (Docker)
In your terminal, run:

```Bash
docker compose up --build -d
```
- Step B: Start the Mouth (Host)
Install the bridge dependencies and run the script:

```Bash
# Windows
pip install flask pychromecast gTTS python-dotenv
python mouth.py

# macOS
pip3 install flask pychromecast gTTS python-dotenv
python3 mouth.py
```
## 🛡️ Privacy & Security
- **Local First**: All AI processing is done on your machine. Your location and data are never sent to external AI providers.
- **Safety**: The SHARED_SECRET ensures that only your SkySentry can trigger your smart speakers.
- **Privacy** : Your actual coordinates are calculated locally from your postcode and are not stored or shared.

## 🤝 Community Calibration
This project is designed for aviation enthusiasts globally. To help others get started, the default calibration in .env.example is set to RAF Coningsby (LN4 4SY), home of the UK's Typhoon display team and the Battle of Britain Memorial Flight.

## 📜 License
MIT License. Explore the skies responsibly!