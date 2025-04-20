from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import base64
import json
from dotenv import load_dotenv

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

@app.route('/location', methods=['POST'])
def location():
    try:
        
        data = request.get_json(force=True)
        print(f"Received location data: {data}")

        
        esp32_id = data.get('esp32_id')
        name = data.get('name')
        lat = data.get('latitude') 
        lon = data.get('longitude') 
        status = data.get('status')  

    
        if not all([esp32_id, name, lat, lon, status]):
            return jsonify({"status": "failure", "error": "Missing required fields"}), 400

        
        ref = db.reference(f'/locations/{name}/{esp32_id}')
        ref.set({
            "latitude": lat,
            "longitude": lon,
            'status': status
        })

        return jsonify({
            "status": "success",
            "esp32_id": esp32_id,
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "status": status
        })
    
    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
