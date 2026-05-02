FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (build tools only if a wheel is missing; slim image keeps it tiny)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/data

# Railway injects $PORT — main.py honors it. Default 8080 for local.
ENV WEBAPP_HOST=0.0.0.0 \
    WEBAPP_PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
