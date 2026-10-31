# Stage 1: Build React frontend (internal tool and upload page for customers)
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    libgles2 libegl1 libgbm1 curl \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MediaPipe models with fixed version and checksum (backend/app/services/analyzer.py)
ENV MODEL_DIR=/app/models
RUN mkdir -p $MODEL_DIR && cd $MODEL_DIR \
    && curl -fsSL -o pose_landmarker_heavy.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task \
    && curl -fsSL -o blaze_face_short_range.tflite https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite \
    && echo "64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b  pose_landmarker_heavy.task" | sha256sum -c - \
    && echo "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f  blaze_face_short_range.tflite" | sha256sum -c -

ENV LIBGL_ALWAYS_SOFTWARE=1
COPY backend/ ./backend/
COPY config/ ./config/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# not as root
RUN useradd --create-home --uid 10001 motavi && chown -R motavi /app
USER motavi

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
