FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.2

WORKDIR /app

# Install system dependencies including PostgreSQL dev headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc build-essential curl \
    && curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && apt-get remove -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .

CMD ["python", "worker.py"]
