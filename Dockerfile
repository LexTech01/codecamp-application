FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    pkg-config \
    libffi-dev \
    shared-mime-info \
    nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p instance app/static/uploads

# Collect static (no-op for Flask, just ensure dir exists)
RUN python3 -c "from app import create_app; app = create_app()" 2>/dev/null || true

EXPOSE 80

COPY nginx.conf /etc/nginx/sites-available/cellusys
RUN ln -sf /etc/nginx/sites-available/cellusys /etc/nginx/sites-enabled/ && \
    rm -f /etc/nginx/sites-enabled/default

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]