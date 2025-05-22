# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.0

# Install python from deadsnakes PPA
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa && \
  apt-get update -y && \
  apt-get install -y --no-install-recommends \
    gdb \
    g++ \
    make \
    python3.11 \
    python3.11-venv \
    python3.11-dev && \
  rm -rf /var/lib/apt/lists/*

# Install poetry
RUN python3.11 -m venv /poetry-env
ENV PATH="/poetry-env/bin:$PATH"
RUN /poetry-env/bin/pip install --no-cache-dir poetry==2.1.1

# The rest of this (for vector tile generation and the server itself) should be easier.
ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_VIRTUALENVS_CREATE=false

# Create a virtual environment for the app; add virtualenv and Poetry to PATH
RUN python3.11 -m venv /venv
ENV PATH="/venv/bin:$PATH" \
    VIRTUAL_ENV=/venv

WORKDIR /app/

COPY pyproject.toml poetry.lock ./
COPY ./deps/ /app/deps/
RUN touch README.md

# Install Poetry dependencies (without dev and local dependencies)
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

# Creating folders, and files for a project:
COPY ./ /app/

# Install the root project and local dependencies
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev

EXPOSE 8000

CMD [ "uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat_tileserver.main:app" ]
