FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# Default entrypoint — expects env vars at runtime
ENTRYPOINT ["python", "-m", "app.main"]
