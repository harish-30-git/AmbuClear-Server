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

load_dotenv()
app = Flask(__name__)
CORS(app)

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
user_queues = {}  # user_id -> list of locations
active_timers = {}  # user_id -> { name -> timer }
TIMEOUT_DURATION = 9 * 60

def revert_to_stop(user_id, name, esp32_id):
    print(f"[{user_id}] Timeout for {name} -> STOP")
    user_queues[user_id] = [item for item in user_queues[user_id] if item["name"] != name]
    ref = db.reference(f'/locations/{name}/{esp32_id}')
    ref.set({ 'status': 'stop' })
    if name in active_timers[user_id]:
        del active_timers[user_id][name]

@app.route("/location", methods=["POST"])
def handle_location():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    esp32_id = data.get("esp32_id")
    name = data.get("name")
    status = data.get("status")

    if not all([user_id, esp32_id, name, status]):
        return jsonify({"status": "failure", "error": "Missing data"}), 400

    if user_id not in user_queues:
        user_queues[user_id] = []
        active_timers[user_id] = {}

    if status == "start":
        if not any(loc["name"] == name for loc in user_queues[user_id]):
            user_queues[user_id].append({
                "name": name,
                "esp32_id": esp32_id,
                "added_at": time()
            })

        # Cancel existing timer
        if name in active_timers[user_id]:
            active_timers[user_id][name].cancel()

        timer = threading.Timer(TIMEOUT_DURATION, revert_to_stop, args=(user_id, name, esp32_id))
        timer.start()
        active_timers[user_id][name] = timer

    elif status == "stop":
        user_queues[user_id] = [item for item in user_queues[user_id] if item["name"] != name]
        if name in active_timers[user_id]:
            active_timers[user_id][name].cancel()
            del active_timers[user_id][name]

    ref = db.reference(f'/locations/{name}/{esp32_id}')
    ref.set({ 'status': status })

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "name": name,
        "status": status
    })

@app.route("/queue", methods=["POST"])
def get_user_queue():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    if not user_id or user_id not in user_queues:
        return jsonify({ "status": "success", "queue": [] })

    queue_names = [item["name"] for item in user_queues[user_id]]
    return jsonify({ "status": "success", "queue": queue_names })

if __name__ == "__main__":
    app.run(debug=True)
