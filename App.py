from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os

app = Flask(__name__)
CORS(app)

service_account_dict = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
    "universe_domain": "googleapis.com"
}

cred = credentials.Certificate(service_account_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ambuclear-ee248-default-rtdb.firebaseio.com/' 
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
    app.run(debug=True)
