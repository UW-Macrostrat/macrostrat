FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/
# https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers

WORKDIR /services/main

ENV UV_COMPILE_BYTECODE=1

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

CMD ["uv", "run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "80"]
