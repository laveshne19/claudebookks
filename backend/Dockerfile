# Nalanda ERP — backend (FastAPI + MongoDB)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Build tools for any packages without prebuilt wheels (cryptography, jq, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# emergentintegrations lives only on the Emergent package index and is OPTIONAL
# at runtime (AI features fall back to deterministic logic when it's absent).
# Install everything else from PyPI, then attempt the Emergent package
# best-effort so the image still builds on a generic host (VPS).
RUN grep -v '^emergentintegrations' requirements.txt > /tmp/req.txt \
    && pip install --upgrade pip \
    && pip install -r /tmp/req.txt \
    && (pip install "emergentintegrations==0.1.0" \
         --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
         || echo "WARN: emergentintegrations unavailable — AI uses fallbacks")

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
