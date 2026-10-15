# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS, cross_origin

# Configure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "src"))

from cnnClassifier import logger
from cnnClassifier.utils.common import decode_image_bytes, decodeImage
from cnnClassifier.pipeline.prediction import PredictionPipeline, get_model, get_class_names

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, send_wildcard=True)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = jsonify({"status": "ok"})
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        res.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "Access-Control-Request-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Access-Control-Request-Private-Network"
        )
        res.headers["Access-Control-Allow-Private-Network"] = "true"
        return res, 200

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Access-Control-Request-Private-Network"
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

SYSTEM_TITLE = "منظومة رداك للتشخيص الشعاعي بالذكاء الاصطناعي (Radiology AI Workstation)"
DEFAULT_PORT = 8081

class ClientApp:
    def __init__(self):
        self.filename = "inputImage.jpg"
        self.classifier = PredictionPipeline()

clApp = ClientApp()

@app.route("/", methods=['GET'])
@cross_origin()
def home():
    """Serves this edition's dedicated clean interface."""
    return render_template("index.html")

@app.route("/sample/<path:filename>", methods=['GET'])
@cross_origin()
def get_sample(filename):
    """Serves test CT scans."""
    samples_dir = os.path.join(current_dir, "test_samples")
    return send_from_directory(samples_dir, filename)

@app.route("/health", methods=['GET'])
@cross_origin()
def health():
    try:
        model = get_model()
        model_ready = model is not None
    except Exception:
        model_ready = False

    return jsonify({
        "status": "healthy" if model_ready else "degraded",
        "system": SYSTEM_TITLE,
        "model_loaded": model_ready,
        "port": DEFAULT_PORT,
        "classes": get_class_names(),
        "accuracy": "93.47%",
        "version": "1.0.0"
    }), 200 if model_ready else 503

@app.route("/api/v1/model-info", methods=['GET'])
@cross_origin()
def model_info():
    scores_file = os.path.join(current_dir, "scores.json")
    metrics = {}
    if os.path.exists(scores_file):
        try:
            with open(scores_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            pass

    return jsonify({
        "model_architecture": "VGG16 Transfer Learning",
        "input_shape": [224, 224, 3],
        "classes": get_class_names(),
        "metrics": metrics,
        "port": DEFAULT_PORT
    })

@app.route("/predict", methods=['POST', 'OPTIONS'])
@app.route("/api/v1/predict", methods=['POST', 'OPTIONS'])
@cross_origin(send_wildcard=True)
def predictRoute():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        if 'file' in request.files or 'image' in request.files:
            file_obj = request.files.get('file') or request.files.get('image')
            if file_obj.filename == '':
                return jsonify({"error": "No file selected."}), 400
            image_bytes = file_obj.read()
        else:
            json_data = request.get_json(silent=True) or {}
            if 'image' in json_data and json_data['image']:
                image_bytes = decode_image_bytes(json_data['image'])
            elif request.data:
                try:
                    raw_json = json.loads(request.data.decode('utf-8'))
                    if 'image' in raw_json and raw_json['image']:
                        image_bytes = decode_image_bytes(raw_json['image'])
                    else:
                        return jsonify({"error": "Image data payload is empty."}), 400
                except Exception:
                    return jsonify({"error": "Invalid payload. Provide base64 JSON {'image': '...'} or multipart form file."}), 400
            else:
                return jsonify({"error": "Invalid payload. Provide base64 JSON {'image': '...'} or multipart form file."}), 400

        detailed_res = clApp.classifier.predict_detailed(image_bytes)

        return jsonify([
            {
                "image": detailed_res["prediction"],
                "prediction": detailed_res["prediction"],
                "arabic_name": detailed_res.get("arabic_name", ""),
                "confidence": detailed_res["confidence"],
                "confidence_percentage": detailed_res["confidence_percentage"],
                "probabilities": detailed_res["probabilities"],
                "risk_level": detailed_res.get("risk_level", "معتدل"),
                "recommendation": detailed_res.get("recommendation", ""),
                "inference_time_ms": detailed_res.get("inference_time_ms", 35),
                "status": "Success",
                "accuracy": "93.47%",
                "port": DEFAULT_PORT
            }
        ])

    except Exception as e:
        logger.exception(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    print("=" * 70)
    print(f"  [STARTING] {SYSTEM_TITLE}")
    print(f"  Port: {port} | URL: http://localhost:{port}/")
    print("=" * 70)
    app.run(host=host, port=port, debug=False)
