FROM python:3.11-slim

# Install basic system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install patchright browsers and their system dependencies automatically
# This is much more robust than a manual list
RUN patchright install chromium
RUN patchright install-deps chromium

# Copy application code
COPY . .

# Render uses the PORT environment variable
ENV PORT=10000
EXPOSE 10000

# Run with single worker and low-memory flags
CMD uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
