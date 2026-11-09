FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# CPU-only PyTorch keeps the image far smaller than the default CUDA build.
# ultralytics installs plain opencv-python, which breaks the contrib build,
# so every opencv package is removed and one is installed again.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt \
    && pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless \
    && pip install "opencv-contrib-python-headless>=4.10,<5" \
    && python -m spacy download en_core_web_sm

RUN useradd --create-home --uid 1000 app && chown app:app /app
USER app

# Download the models at build time so the container starts fast
# and never needs internet access at runtime.
RUN python -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_small-v2.1')" \
    && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY --chown=app:app app ./app

ENV HF_HUB_OFFLINE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# ONE worker on purpose: the privacy vault lives in this process's memory.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
