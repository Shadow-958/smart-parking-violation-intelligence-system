# Build context is the project root (see docker-compose.yml), not this
# backend/ folder, so this image can also COPY in ai_models/ — code that
# lives outside backend/ but is imported by it.

FROM python:3.11-slim

# System dependencies needed for PostgreSQL / GDAL.
# OpenCV is installed as the headless variant below, so no GUI libraries
# are required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------------------------------------
# Core backend dependencies
# ---------------------------------------------------------
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# NLP / AI dependencies
# ---------------------------------------------------------
COPY backend/requirements-ai.txt ./requirements-ai.txt
RUN pip install --no-cache-dir -r requirements-ai.txt

RUN python -m spacy download en_core_web_sm

RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet')"

# ---------------------------------------------------------
# Computer Vision dependencies
# ---------------------------------------------------------
COPY backend/requirements-cv.txt ./requirements-cv.txt

# Install CV dependencies first. torch/torchvision are pinned in
# requirements-cv.txt so ultralytics cannot upgrade PyTorch to 2.6+.
RUN pip install --no-cache-dir -r requirements-cv.txt

# Replace GUI OpenCV (pulled in by ultralytics) with the headless
# version suitable for Docker.
RUN pip uninstall -y opencv-python opencv-contrib-python || true \
    && pip install --no-cache-dir --force-reinstall \
        opencv-python-headless==4.10.0.84 \
        numpy==1.26.4

# Ultralytics 8.2.58 calls torch.load without weights_only=False.
# Harmless on torch 2.3.1; required if a newer torch is present.
ENV TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1

# Verify installed AI package versions
RUN python -c "import torch; print('PyTorch version:', torch.__version__); import ultralytics; print('Ultralytics version:', ultralytics.__version__)"

# Download YOLOv8 weights and verify Ultralytics can load.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
# ---------------------------------------------------------
# Machine Learning dependencies
# ---------------------------------------------------------
COPY backend/requirements-ml.txt ./requirements-ml.txt
RUN pip install --no-cache-dir -r requirements-ml.txt

# ---------------------------------------------------------
# Application source
# ---------------------------------------------------------
COPY backend/ .
COPY ai_models/ ./ai_models/

RUN mkdir -p ai_models/ml_prediction/artifacts

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]