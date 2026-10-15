import os
import io
import time
import logging
from typing import List, Dict, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cnnClassifier.utils.common import decode_image_bytes
from cnnClassifier.pipeline.prediction import PredictionPipeline, get_model

logger = logging.getLogger("cnnClassifierLogger")

app = FastAPI(
    title="Kidney Disease Classification AI Service",
    description="Enterprise Deep Learning Inference API for Kidney CT Scan Diagnosis (Normal vs Tumor). Powered by Transfer Learning CNNs (VGG16).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-origin frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = PredictionPipeline()


# ------------------ Pydantic Data Contracts ------------------

class Base64PredictionRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded string of the Kidney CT scan image (with or without data URI prefix)")

class BatchPredictionRequest(BaseModel):
    images: List[str] = Field(..., description="List of base64 encoded strings of Kidney CT scan images")

class PredictionResponse(BaseModel):
    prediction: str = Field(..., example="Tumor", description="Diagnostic classification label (Normal, Tumor, Cyst, Stone)")
    class_index: int = Field(..., example=3, description="Numerical index of predicted class")
    confidence: float = Field(..., example=0.9852, description="Prediction confidence score (0 to 1)")
    confidence_percentage: str = Field(..., example="98.52%", description="Prediction confidence percentage")
    probabilities: Dict[str, float] = Field(..., description="Full probability distribution over all diagnostic classes")
    risk_level: str = Field(..., example="High Risk", description="Clinical risk rating")
    inference_time_ms: float = Field(..., example=42.15, description="Model latency in milliseconds")
    model_version: str = Field(..., example="VGG16-TransferLearning-v1", description="Model architecture identifier")

class HealthStatusResponse(BaseModel):
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="kidney-disease-classifier-fastapi")
    model_loaded: bool = Field(..., example=True)
    version: str = Field(..., example="1.0.0")

class ModelInfoResponse(BaseModel):
    model_architecture: str = Field(..., example="VGG16 Transfer Learning")
    input_shape: List[int] = Field(..., example=[224, 224, 3])
    classes: List[str] = Field(..., example=["Cyst", "Normal", "Stone", "Tumor"])
    framework: str = Field(..., example="TensorFlow / Keras")
    task: str = Field(..., example="Multi-class Kidney CT Image Classification")


# ------------------ API Endpoints ------------------

@app.get("/health", response_model=HealthStatusResponse, tags=["Monitoring & Probes"])
async def health_check():
    """Liveness and readiness check for Kubernetes and AWS load balancers."""
    try:
        model = get_model()
        is_ready = model is not None
    except Exception:
        is_ready = False

    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "service": "kidney-disease-classifier-fastapi",
                "model_loaded": False,
                "version": "1.0.0"
            }
        )

    return {
        "status": "healthy",
        "service": "kidney-disease-classifier-fastapi",
        "model_loaded": True,
        "version": "1.0.0"
    }


@app.get("/api/v1/model-info", response_model=ModelInfoResponse, tags=["Metadata"])
async def get_model_info():
    """Returns technical metadata about the underlying CNN classifier."""
    from cnnClassifier.pipeline.prediction import get_class_names
    classes = get_class_names(4)
    return {
        "model_architecture": "VGG16 Transfer Learning",
        "input_shape": [224, 224, 3],
        "classes": classes,
        "framework": "TensorFlow / Keras",
        "task": "Multi-class Kidney CT Image Classification"
    }


@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict_base64(payload: Base64PredictionRequest):
    """
    Perform deep learning inference on a base64 encoded CT scan image.
    """
    try:
        if not payload.image or len(payload.image.strip()) < 10:
            raise HTTPException(status_code=400, detail="Invalid or empty image payload.")

        image_bytes = decode_image_bytes(payload.image)
        result = pipeline.predict_detailed(image_bytes)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@app.post("/api/v1/predict/file", response_model=PredictionResponse, tags=["Inference"])
async def predict_file(file: UploadFile = File(..., description="Kidney CT scan image file (.jpg, .png, .jpeg)")):
    """
    Perform deep learning inference directly on an uploaded image file (multipart/form-data).
    """
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File must be an image, received: {file.content_type}")

        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        result = pipeline.predict_detailed(image_bytes)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"File inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@app.post("/api/v1/predict/batch", response_model=List[PredictionResponse], tags=["Inference"])
async def predict_batch(payload: BatchPredictionRequest):
    """
    Perform batch inference on multiple CT scan images.
    """
    if len(payload.images) > 32:
        raise HTTPException(status_code=400, detail="Batch size limit exceeded. Maximum 32 images per batch.")

    results = []
    for idx, b64_img in enumerate(payload.images):
        try:
            img_bytes = decode_image_bytes(b64_img)
            res = pipeline.predict_detailed(img_bytes)
            results.append(res)
        except Exception as e:
            logger.warning(f"Failed processing image at index {idx}: {e}")
            raise HTTPException(status_code=400, detail=f"Error at image index {idx}: {str(e)}")

    return results


def _serve_template(filename: str):
    path = os.path.join("templates", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(f"<h2>Template {filename} not found.</h2>", status_code=404)


@app.get("/", response_class=HTMLResponse, tags=["User Interface"])
async def ui():
    """Serves the medical diagnostic dashboard based on APP_THEME or default."""
    theme = os.getenv("APP_THEME", "clinical").lower().strip()
    theme_map = {
        "clinical": "index_clinical.html",
        "radiology": "index_radiology_dark.html",
        "biotech": "index_biotech_glass.html",
        "standard": "index.html"
    }
    target_file = theme_map.get(theme, "index_clinical.html")
    return _serve_template(target_file)


@app.get("/clinical", response_class=HTMLResponse, tags=["User Interface"])
async def ui_clinical():
    """Version 1: Clinical Cleanroom Edition (Hospital-grade white theme)."""
    return _serve_template("index_clinical.html")


@app.get("/radiology", response_class=HTMLResponse, tags=["User Interface"])
async def ui_radiology():
    """Version 2: Radiology Dark Suite (Linear / PACS dark workstation)."""
    return _serve_template("index_radiology_dark.html")


@app.get("/biotech", response_class=HTMLResponse, tags=["User Interface"])
async def ui_biotech():
    """Version 3: Futuristic Biotech Glassmorphism Edition."""
    return _serve_template("index_biotech_glass.html")
