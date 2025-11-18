FROM python:3.11-slim

# Systempakete (Poppler + Tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Setze Thread-Limits damit numpy/scikit/sentence-transformers nicht alle CPUs fressen
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    OCR_CONCURRENCY=1 \
    CHROMA_DISABLE_TELEMETRY=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY . .

# non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

EXPOSE 8000

CMD ["python", "bot.py"]