# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here

FROM python:3.9@sha256:c0dcc146710fed0a6d62cb55b92f00bfbfc3b931fff6218f4958bab58333c37b

# Install UV for Python package management
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_SYSTEM_PYTHON=0
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

WORKDIR /services/main

# Create and enter a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Install MAPNIK
# Install dependencies for compiling legacy image tiles
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  build-essential software-properties-common curl \
  libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
  libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
  libfreetype-dev libpng-dev libxml2-dev libproj-dev libcairo-dev \
  postgresql-contrib libharfbuzz-dev python-dev && \
  rm -rf /var/lib/apt/lists/*

# Mapnik
ARG MAPNIK_VERSION=3.1.0
RUN curl -L -s https://github.com/mapnik/mapnik/releases/download/v${MAPNIK_VERSION}/mapnik-v${MAPNIK_VERSION}.tar.bz2 | tar -xj -C /tmp/
RUN cd /tmp/mapnik-v${MAPNIK_VERSION} && python scons/scons.py configure
RUN cd /tmp/mapnik-v${MAPNIK_VERSION} && make JOBS=4 && make install JOBS=4

ENV BOOST_PYTHON_LIB=boost_python39
# Build/install Mapnik Python bindings
ARG PYTHON_MAPNIK_COMMIT=7da019cf9eb12af8f8aa88b7d75789dfcd1e901b
RUN mkdir -p /opt/python-mapnik && curl -L https://github.com/mapnik/python-mapnik/archive/${PYTHON_MAPNIK_COMMIT}.tar.gz | tar xz -C /opt/python-mapnik --strip-components=1

# Carto is needed for CartoCSS -> Mapnik XML conversion
# Install Node.js and npm
# Import the Node.js repository GPG key
RUN apt-get update -y && \
  apt-get install -y nodejs npm && \
  npm install -g carto && \
  rm -rf /tmp/* && \
  rm -rf /var/lib/apt/lists/*

RUN uv pip install /opt/python-mapnik

# Remove build dependencies
RUN apt-get remove -y \
  build-essential software-properties-common \
  libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
  libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
  libfreetype-dev libpng-dev libxml2-dev libproj-dev libcairo-dev libharfbuzz-dev python-dev

# NEED TO specify a build context for the py-modules directory
COPY --from=py-modules tileserver-utils /py-modules/tileserver-utils

# Install dependencies. The --inexact flag allows us to keep the unmanaged mapnik installation
# even though it is not specified in the lockfile.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --inexact --locked --no-install-project --no-editable --active

# We've already built this but we have to reinstall it after uv sync
RUN uv pip install /opt/python-mapnik && \
    rm -rf /opt/python-mapnik

# Add source files to project
ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --inexact --locked --no-editable --active

# Check whether Mapnik bindings are properly installed
RUN python -c "import mapnik; print('mapnik version:', mapnik.mapnik_version())" && \
    python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)"

EXPOSE 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.legacy_tileserver:app"]

