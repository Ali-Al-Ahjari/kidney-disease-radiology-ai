# Contributing to Kidney Disease Radiology AI Workstation

Thank you for your interest in contributing to the **Kidney Disease Radiology AI Workstation**! We welcome contributions from machine learning practitioners, medical researchers, radiologists, and software engineers.

---

## 📋 Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Model Training & Evaluation Guidelines](#model-training--evaluation-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs & Requesting Features](#reporting-bugs--requesting-features)

---

## 🤝 Code of Conduct
Please be respectful, professional, and constructive in all issues, pull requests, and discussions.

---

## 🛠 Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/Ali-Al-Ahjari/kidney-disease-radiology-ai.git
   cd kidney-disease-radiology-ai
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies in Editable Mode**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Verify Offline Workstation & Model Loading**:
   ```bash
   python verify_offline.py
   ```

5. **Start the Local Server**:
   ```bash
   python launch.py
   # or
   python app.py
   ```
   Open `http://localhost:8081` in your browser.

---

## 🔬 Model Training & Evaluation Guidelines
- Pipeline stages are modularly organized under `src/cnnClassifier/pipeline/`:
  - `stage_01_data_ingestion.py`
  - `stage_02_prepare_base_model.py`
  - `stage_03_model_training.py`
  - `stage_04_model_evaluation.py`
- All hyperparameters must be declared in `params.yaml`.
- When fine-tuning, save performance metrics (accuracy, per-class F1, confusion matrix) to `scores.json`.
- Any weights updated to `model/model.h5` must undergo validation against the 4-class benchmark (Cyst, Normal, Stone, Tumor).

---

## 🚀 Pull Request Process

1. Create a dedicated branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Follow PEP 8 guidelines for Python code.
3. Ensure no unneeded files (`.venv/`, `__pycache__/`, logs) are tracked.
4. Run `python verify_offline.py` to confirm zero regression.
5. Push to your fork and submit a Pull Request describing your changes, test results, and impact.

---

## 🩺 Medical Disclaimer
This software is designed as a computer-aided diagnosis research tool and clinical assistance system. It is not intended as a sole replacement for certified radiological consultation or histological biopsy confirmation.
