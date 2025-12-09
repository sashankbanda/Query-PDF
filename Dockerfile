# Use a lightweight Python base
FROM python:3.11-slim

# 1. Install System Dependencies (Tesseract & Poppler)
# We add '--no-install-recommends' to keep the image small
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy requirements first to leverage Docker cache
COPY requirements.txt .

# 3. CRITICAL: Install CPU-only PyTorch explicitly BEFORE other requirements
# This prevents downloading the massive GPU version
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 4. Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 5. Run the app
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120