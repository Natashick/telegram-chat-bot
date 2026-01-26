# Dockerfile
FROM python:3.11-slim

# Systempakete (Poppler + Tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# CPU-only PyTorch for sentence-transformers
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1

# Thread limits to prevent oversubscription
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    OCR_CONCURRENCY=1 \
    CHROMA_DISABLE_TELEMETRY=1 \
    PYTHONUNBUFFERED=1

# App requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status==200 else sys.exit(1)" || exit 1

CMD ["sh","-c","gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 --access-logfile - bot:app"]