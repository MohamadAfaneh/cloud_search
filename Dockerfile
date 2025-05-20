FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    curl \
    openssl \
    libmagic1 \
    file \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

ENV TESSERACT_CMD=/usr/bin/tesseract

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/downloads /app/data /app/certs && \
    chmod 777 /app/downloads /app/data /app/certs

COPY . .

RUN chmod +x /app/create_certs.py /app/docker-entrypoint.sh

RUN tesseract --version && \
    tesseract --list-langs

EXPOSE 8443

ENTRYPOINT ["/app/docker-entrypoint.sh"]