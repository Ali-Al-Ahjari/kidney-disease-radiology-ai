import os
import time
import io
import json
import threading
import logging
from typing import Union, Dict, Any, List, Optional
from pathlib import Path

import numpy as np
from PIL import Image

# Lazy/cached imports for TensorFlow to optimize startup and support graceful fallbacks
_model_instance = None
_model_lock = threading.Lock()
logger = logging.getLogger("cnnClassifierLogger")

DEFAULT_CLASSES = ["Cyst", "Normal", "Stone", "Tumor"]
CLASS_NAMES = DEFAULT_CLASSES
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CLASSES_PATH = str(PROJECT_ROOT / "model" / "classes.json")
DEFAULT_MODEL_PATH = str(PROJECT_ROOT / "model" / "model.h5")


def get_class_names(num_classes: int = 4) -> List[str]:
    """
    Returns registered class names.
    Checks model/classes.json if present; otherwise falls back based on output dimension.
    """
    if os.path.exists(DEFAULT_CLASSES_PATH):
        try:
            with open(DEFAULT_CLASSES_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and len(loaded) == num_classes:
                    return loaded
        except Exception as e:
            logger.warning(f"Could not load classes.json: {e}")

    if num_classes == 2:
        return ["Normal", "Tumor"]
    elif num_classes == 4:
        return ["Cyst", "Normal", "Stone", "Tumor"]
    else:
        return [f"Class_{i}" for i in range(num_classes)]


def ensure_model_weights(path: str) -> str:
    """
    Ensures that the model weights file exists and is a valid neural network binary.
    1. If model.h5 exists and is full size (> 100MB), uses it directly.
    2. If missing or incomplete, checks for model.h5.part1 & model.h5.part2 and reassembles instantly.
    3. If parts are missing, attempts downloading from official GitHub Release assets.
    """
    if os.path.exists(path) and os.path.getsize(path) > 100000000:
        return path

    part1 = path + ".part1"
    part2 = path + ".part2"

    if os.path.exists(part1) and os.path.exists(part2):
        logger.info(f"Reassembling model weights from split packages: {part1} + {part2}...")
        try:
            with open(path, "wb") as f_out:
                for p in [part1, part2]:
                    with open(p, "rb") as f_in:
                        f_out.write(f_in.read())
            logger.info(f"Model reassembled successfully ({os.path.getsize(path)} bytes).")
            return path
        except Exception as e:
            logger.warning(f"Error reassembling model parts: {e}")

    # Fallback to GitHub Release download if parts are not present
    release_url = "https://github.com/Ali-Al-Ahjari/kidney-disease-radiology-ai/releases/download/v1.0.0/model.h5"
    logger.info(f"Model weights file '{path}' missing. Downloading pre-trained VGG16 model from {release_url}...")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    try:
        import urllib.request
        urllib.request.urlretrieve(release_url, path)
        logger.info("Model weights downloaded successfully.")
    except Exception as e:
        logger.warning(f"Could not automatically download model from release URL: {e}")

    return path


def get_model(model_path: Optional[str] = None):
    """
    Thread-safe Singleton Model Loader.
    Loads model once into memory and reuses across concurrent requests.
    """
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    with _model_lock:
        if _model_instance is None:
            path = model_path or os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
            if not os.path.exists(path) or (os.path.exists(path) and os.path.getsize(path) < 2048):
                # Search common fallback paths
                alt_paths = [
                    os.path.join("model", "model.h5"),
                    str(PROJECT_ROOT / "artifacts" / "training" / "model.h5"),
                    os.path.join("artifacts", "training", "model.h5"),
                    str(PROJECT_ROOT / "artifacts" / "prepare_base_model" / "base_model_updated.h5"),
                    os.path.join("artifacts", "prepare_base_model", "base_model_updated.h5"),
                ]
                for alt in alt_paths:
                    if os.path.exists(alt) and os.path.getsize(alt) > 2048:
                        path = alt
                        break

            path = ensure_model_weights(path)

            if not os.path.exists(path):
                raise FileNotFoundError(f"Model file not found at: {path}")

            logger.info(f"Loading deep learning model from {path} into memory...")
            start_time = time.time()
            from tensorflow.keras.models import load_model
            _model_instance = load_model(path)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Model loaded successfully in {elapsed:.2f}ms")

    return _model_instance



def reset_model():
    """Forces reloading model on disk (used after retraining)."""
    global _model_instance
    with _model_lock:
        _model_instance = None


def preprocess_image(image_input: Union[str, bytes, Image.Image, io.BytesIO], target_size=(224, 224)) -> np.ndarray:
    """
    Preprocess image input into model-ready numpy batch array.
    Handles:
    - String paths
    - In-memory bytes / BytesIO
    - PIL Image objects
    - Color mode conversion (RGBA/L -> RGB)
    - Resizing and [0, 1] normalization matching training generator
    """
    if isinstance(image_input, (str, Path)):
        pil_img = Image.open(str(image_input))
    elif isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, io.BytesIO):
        pil_img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        pil_img = image_input
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    # Ensure 3-channel RGB (CT scans can be grayscale or contain alpha channel)
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # Resize to model target size
    pil_img = pil_img.resize(target_size, Image.Resampling.BILINEAR)

    # Convert to array & normalize to [0, 1] matching training pipeline
    img_array = np.array(pil_img, dtype=np.float32) / 255.0

    # Add batch dimension: (1, 224, 224, 3)
    img_tensor = np.expand_dims(img_array, axis=0)
    return img_tensor


class PredictionPipeline:
    """
    Production-ready prediction pipeline.
    Maintains backward compatibility with legacy app.py while providing
    full clinical probabilities, confidence scores, and latency metrics.
    """
    def __init__(self, filename: Optional[str] = None, model_path: Optional[str] = None):
        self.filename = filename
        self.model_path = model_path
        # Pre-warm model in background / init
        try:
            self.model = get_model(self.model_path)
        except Exception as e:
            logger.warning(f"Model not immediately preloaded: {e}")
            self.model = None

    def predict(self, image_data: Optional[Union[str, bytes, Image.Image]] = None) -> List[Dict[str, Any]]:
        """
        Legacy compatible predict method returning [{ "image" : prediction }].
        Also includes extended metadata fields.
        """
        detailed = self.predict_detailed(image_data)
        return [{
            "image": detailed["prediction"],
            "prediction": detailed["prediction"],
            "confidence": detailed["confidence"],
            "confidence_percentage": detailed["confidence_percentage"],
            "probabilities": detailed["probabilities"],
            "risk_level": detailed["risk_level"],
            "inference_time_ms": detailed["inference_time_ms"]
        }]

    def predict_detailed(self, image_data: Optional[Union[str, bytes, Image.Image]] = None) -> Dict[str, Any]:
        """
        Production inference method with full clinical diagnostics metrics.
        """
        target = image_data if image_data is not None else self.filename
        if target is None:
            raise ValueError("No image provided for prediction.")

        model = get_model(self.model_path)
        processed_img = preprocess_image(target, target_size=(224, 224))

        start_time = time.perf_counter()
        raw_predictions = model.predict(processed_img, verbose=0)
        inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        probs = raw_predictions[0]
        num_outputs = len(probs)
        classes = get_class_names(num_outputs)

        if num_outputs == 1:
            # Single sigmoid fallback
            val = float(probs[0])
            probs_dict = {"Normal": round(1.0 - val, 4), "Tumor": round(val, 4)}
            predicted_idx = 1 if val >= 0.5 else 0
            prediction_label = "Tumor" if predicted_idx == 1 else "Normal"
            confidence = val if predicted_idx == 1 else (1.0 - val)
        else:
            predicted_idx = int(np.argmax(probs))
            prediction_label = classes[predicted_idx] if predicted_idx < len(classes) else f"Class_{predicted_idx}"
            confidence = float(probs[predicted_idx])
            probs_dict = {
                cls_name: round(float(p), 4)
                for cls_name, p in zip(classes, probs)
            }

        # Clinical Diagnostic & Risk Mapping
        arabic_names = {
            "Tumor": "ورم كلوي مشتبه به (Renal Tumor)",
            "Stone": "حصوة كلوية متكلسة (Nephrolithiasis)",
            "Cyst": "كيس كلوي سائل (Renal Cyst)",
            "Normal": "نسيج كلوي سليم وطبيعي (Normal Tissue)"
        }

        recommendations = {
            "Tumor": "يوصى بمراجعة استشاري جراحة الأورام والمسالك البولية لإجراء فحص رنين مغناطيسي (MRI) وتحديد بروتوكول الرعاية العاجل.",
            "Stone": "يوصى بمراجعة طبيب المسالك البولية لتقييم موقع وحجم الحصوة وتحديد العلاج الدوائي أو التفتيت بالموجات التصادمية.",
            "Cyst": "يوصى بالمتابعة الدورية بالموجات فوق الصوتية (Ultrasound) لتقييم حجم الكيس ومتابعته وفق تصنيف بوزنياك (Bosniak).",
            "Normal": "النسيج الكلوي المقطعي يبدو متجانساً وسليماً بدون أي كتل أو حصوات أو أكياس ظاهرة. يوصى بالفحص الدوري الروتيني."
        }

        risk_mapping = {
            "Tumor": "عالي (High Risk - ورم مشتبه به)",
            "Stone": "متوسط (Moderate Risk - حصوة كلوية)",
            "Cyst": "متوسط (Moderate Risk - كيس كلوي)",
            "Normal": "منخفض (Low Risk - سليم وطبيعي)"
        }

        risk_level = risk_mapping.get(prediction_label, "غير محدد (Unspecified)")
        arabic_name = arabic_names.get(prediction_label, prediction_label)
        recommendation = recommendations.get(prediction_label, "يوصى بمراجعة الطبيب المختص.")

        return {
            "prediction": prediction_label,
            "arabic_name": arabic_name,
            "class_index": predicted_idx,
            "confidence": round(confidence, 4),
            "confidence_percentage": f"{confidence * 100:.2f}%",
            "probabilities": probs_dict,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "inference_time_ms": inference_time_ms,
            "model_version": "VGG16-TransferLearning-v1"
        }