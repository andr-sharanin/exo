FROM python:3.12-slim

WORKDIR /app

# System dependencies for asyncpg and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache — only rebuilds when pyproject.toml changes)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source after dependencies (maximize cache hits)
COPY . .

EXPOSE 8000

# Production: remove --reload. Development override in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
