from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
CORS(app)


cred = credentials.Certificate("path/to/your-service-account.json")
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

        return jsonify({"status": "success", "esp32_id": esp32_id, "name": name, "latitude": lat, "longitude": lon, "status": status})
    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
