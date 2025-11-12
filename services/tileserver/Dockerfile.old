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
COPY ./deps/timvt_local ./deps/timvt_local
RUN touch README.md

# Install Poetry dependencies (without dev and local dependencies)
RUN --mount=type=cache,target=$POETRY_CACHE_DIR /poetry-env/bin/poetry install --without dev --without local --no-root

# Remove build dependencies
RUN apt-get remove -y \
  software-properties-common \
  g++ \
  make \
  python3.11-dev && \
  rm -rf /var/lib/apt/lists/*

# Copy local wheels and install with pip
# TODO: place these wheels in a package repository to separate their build process...
COPY ./deps/*.whl ./deps/
# Install local wheels without caring about hashes (poetry gets mad if package hashes don't match.
# Non-matching hashes could result from a different build environment (e.g, the wheel was compiled/locked locally
# and the Dockerfile is now being built in CI/CD).
# This is a temporary solution until we can get the wheels into a package repository.
RUN pip install --no-cache-dir ./deps/*.whl

# Creating folders and files for a project, including remaining local wheels
COPY ./ /app/

# Install the root project and local dependencies
RUN --mount=type=cache,target=$POETRY_CACHE_DIR /poetry-env/bin/poetry install --without dev

# Remove Poetry and other versions of python
RUN rm -rf /poetry-env && rm -rf /usr/lib/python3.12

EXPOSE 8000

CMD [ "uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.tileserver:app" ]
