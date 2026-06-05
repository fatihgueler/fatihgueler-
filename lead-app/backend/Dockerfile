# Backend-Image für Railway (FastAPI + Scrapling).
# Schlank: die Web-App nutzt nur den HTTP-Fetcher (Overpass + DuckDuckGo),
# also KEINE Browser-Binaries nötig.
FROM python:3.11-slim

# TLS-Zertifikate für ausgehende HTTPS-Requests
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injiziert $PORT zur Laufzeit
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
