FROM python:3.11-slim

# Install system dependencies for OCR, Forensics, and DB
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-mar \
    libgl1-mesa-glx \
    libglib2.0-0 \
    exiftool \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm && \
    python -m spacy download xx_ent_wiki_sm

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app/python
ENV HOST=0.0.0.0

EXPOSE 8765

WORKDIR /app/python
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8765"]
