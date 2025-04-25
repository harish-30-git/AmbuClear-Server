from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import base64
import json
from dotenv import load_dotenv
import threading

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

TIMEOUT_DURATION = 60000 

user_queues = {}
active_timers = {}

def revert_to_stop(name, esp32_id, user_id):
    print(f"[Timeout] Reverting {name} to stop for user {user_id}")
    try:
        if user_id in user_queues and name in user_queues[user_id]:
            user_queues[user_id].remove(name)
        ref = db.reference(f'/locations/{name}/{esp32_id}/{user_id}')
        ref.set({'status': 'stop'})
    except Exception as e:
        print(f"Error reverting status: {e}")

@app.route('/location', methods=['POST'])
def location():
    try:
        data = request.get_json(force=True)
        print(f"Received: {data}")

        user_id = data.get('user_id')
        esp32_id = data.get('esp32_id')
        name = data.get('name')
        status = data.get('status')

        if not all([user_id, esp32_id, name, status]):
            return jsonify({"status": "failure", "error": "Missing required fields"}), 400

        if user_id not in user_queues:
            user_queues[user_id] = []

        if status == "start":
            if name not in user_queues[user_id]:
                user_queues[user_id].append(name)

            timer_key = f"{user_id}_{name}"
            if timer_key in active_timers:
                active_timers[timer_key].cancel()

            timer = threading.Timer(TIMEOUT_DURATION / 1000, revert_to_stop, args=(name, esp32_id, user_id))
            timer.start()
            active_timers[timer_key] = timer

        elif status == "stop":
            if name in user_queues[user_id]:
                user_queues[user_id].remove(name)

            timer_key = f"{user_id}_{name}"
            if timer_key in active_timers:
                active_timers[timer_key].cancel()
                del active_timers[timer_key]

        ref = db.reference(f'/locations/{name}/{esp32_id}/{user_id}')
        ref.set({'status': status})

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "name": name,
            "status": status
        })

    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500

@app.route('/queue', methods=['GET'])
def get_queue():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"status": "failure", "error": "Missing user_id"}), 400

    queue = user_queues.get(user_id, [])
    return jsonify({
        "status": "success",
        "queue": queue
    })

if __name__ == '__main__':
    app.run(deebug=True)
