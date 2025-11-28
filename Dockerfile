FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system deps for Chrome/Chromedriver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        libnss3 \
        libxss1 \
        libasound2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CHROME_BINARY=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides PORT; default to 8000 locally
ENV PORT=8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
