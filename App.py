from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import base64
import json
from dotenv import load_dotenv
import threading
from time import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Firebase initialization
firebase_creds_b64 = os.getenv("FIREBASE_CONFIG_BASE64")
if not firebase_creds_b64:
    raise ValueError("Missing FIREBASE_CONFIG_BASE64 in .env")

decoded_creds = base64.b64decode(firebase_creds_b64).decode('utf-8')
firebase_creds = json.loads(decoded_creds)

cred = credentials.Certificate(firebase_creds)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("FIREBASE_DB_URL")
})

# Globals
queue = []
active_timers = {}

# Timeout duration in seconds (9 minutes)
TIMEOUT_DURATION = 9 * 60  # 540 seconds

# Revert location status to 'stop' after timeout
def revert_to_stop(name, esp32_id):
    print(f"Timeout reached for {name}. Reverting status to 'stop'")
    try:
        global queue, active_timers
        queue = [item for item in queue if item["name"] != name]

        ref = db.reference(f'/locations/{name}/{esp32_id}')
        ref.set({
            'status': 'stop'
        })

        if name in active_timers:
            del active_timers[name]

    except Exception as e:
        print(f"Error reverting status: {e}")

# Location update endpoint
@app.route('/location', methods=['POST'])
def location():
    global queue, active_timers
    try:
        data = request.get_json(force=True)
        print(f"Received location data: {data}")
        esp32_id = data.get('esp32_id')
        name = data.get('name')
        status = data.get('status')

        if not all([esp32_id, name, status]):
            return jsonify({"status": "failure", "error": "Missing required fields"}), 400

        # Handle 'start' status
        if status == "start":
            if not any(item["name"] == name for item in queue):
                queue.append({
                    "name": name,
                    "esp32_id": esp32_id,
                    "added_at": time()
                })

            # Cancel existing timer if any
            if name in active_timers:
                active_timers[name].cancel()

            # Start a new timer
            timer = threading.Timer(TIMEOUT_DURATION, revert_to_stop, args=(name, esp32_id))
            timer.start()
            active_timers[name] = timer

        # Handle 'stop' status
        elif status == "stop":
            queue = [item for item in queue if item["name"] != name]

            # Cancel and remove the timer
            if name in active_timers:
                active_timers[name].cancel()
                del active_timers[name]

        # Update Firebase
        ref = db.reference(f'/locations/{name}/{esp32_id}')
        ref.set({
            'status': status
        })

        return jsonify({
            "status": "success",
            "esp32_id": esp32_id,
            "name": name,
            "status": status
        })

    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500

# Endpoint to get current queue (only names)
@app.route('/queue', methods=['GET'])
def get_queue():
    try:
        formatted_queue = [item["name"] for item in queue]

        return jsonify({
            "status": "success",
            "queue": formatted_queue
        })

    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
