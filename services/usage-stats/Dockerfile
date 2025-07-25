# Use official Python slim image
FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.2

# Set working directory
WORKDIR /app

# Install Poetry and system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential gcc \
    && curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && apt-get remove -y curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files (for better cache)
COPY pyproject.toml poetry.lock ./

# Disable Poetry virtualenvs and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copy the full project
COPY . .

# Run the worker script
CMD ["python", "worker.py"]
