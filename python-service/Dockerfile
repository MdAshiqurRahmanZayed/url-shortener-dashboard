FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup && useradd -r -g appgroup appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates/ ./templates/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:5000/ || exit 1

CMD ["python", "app.py"]
