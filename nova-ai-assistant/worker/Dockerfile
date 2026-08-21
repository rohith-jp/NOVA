# ============================================================
# NOVA Celery Worker (Python 3.12)
# Runs browser_tasks (Playwright) + general tasks
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ─── System dependencies ─────────────────────────────────────
# Playwright Chromium needs a full set of system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    curl \
    # Playwright / Chromium runtime deps
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Python dependencies ─────────────────────────────────────
# Worker has its own requirements.txt that mirrors backend's core deps
COPY worker/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to keep image lean)
RUN playwright install chromium --with-deps || playwright install chromium

# ─── Application source ──────────────────────────────────────
# Copy both backend (for shared app.* imports) and worker packages
COPY backend/ ./backend/
COPY worker/ ./worker/

# Ensure Python can find both packages
ENV PYTHONPATH=/app:/app/backend

# ─── Start Celery worker ─────────────────────────────────────
# prefork pool, 2 concurrent processes (tune via CELERYD_CONCURRENCY)
CMD ["sh", "-c", "celery -A worker.celery_app worker --loglevel=info --concurrency=${CELERYD_CONCURRENCY:-2}"]
