# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin

# Create a non-root user for running the application
# This prevents security warnings when running Celery workers
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

COPY . .

# Create media directories with proper permissions before switching user
RUN mkdir -p /app/media/profile_photos/staff \
    && mkdir -p /app/media/profile_photos/supplier \
    && mkdir -p /app/media/profile_photos/reseller \
    && chmod +x entrypoint.sh \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh", "gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]

