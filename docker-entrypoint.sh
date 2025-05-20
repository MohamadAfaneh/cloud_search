#!/bin/bash
set -e

mkdir -p /app/certs

if [ ! -f /app/certs/server.crt ]; then
    echo "Generating self-signed certificates..."
    cd /app
    python create_certs.py
    echo "Certificate generation completed"
    ls -la /app/certs
fi

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile /app/certs/server.key --ssl-certfile /app/certs/server.crt 