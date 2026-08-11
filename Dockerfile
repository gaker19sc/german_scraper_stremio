FROM python:3.11-slim

# Install system dependencies for Playwright and ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install patchright browsers (Chromium only to save space/RAM)
RUN patchright install chromium

# Copy application code
COPY . .

# Render uses the PORT environment variable
ENV PORT=10000
EXPOSE 10000

# Run with single worker to save memory
CMD uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
