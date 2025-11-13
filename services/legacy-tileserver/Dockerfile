# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here

FROM python:3.9@sha256:c0dcc146710fed0a6d62cb55b92f00bfbfc3b931fff6218f4958bab58333c37b

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV=/venv

# MAPNIK
# Install mapnik for compiling legacy image tiles
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
# Python bindings to mapnik
ARG PYTHON_MAPNIK_COMMIT=7da019cf9eb12af8f8aa88b7d75789dfcd1e901b
RUN mkdir -p /opt/python-mapnik && curl -L https://github.com/mapnik/python-mapnik/archive/${PYTHON_MAPNIK_COMMIT}.tar.gz | tar xz -C /opt/python-mapnik --strip-components=1
RUN cd /opt/python-mapnik && python3 setup.py install && rm -r /opt/python-mapnik/build

# Remove build dependencies
RUN apt-get remove -y \
  build-essential software-properties-common \
  libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
  libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
  libfreetype-dev libpng-dev libxml2-dev libproj-dev libcairo-dev libharfbuzz-dev python-dev

# CartoCSS stylesheet generation
# Install nodejs
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash - && \
  apt-get install -y nodejs && \
  rm -rf /var/lib/apt/lists/*

# Install carto
RUN npm install -g carto

# Clear temporary files
RUN rm -rf /tmp/*

# The rest of this (for the server itself) should be easier.

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# NEED TO specify a build context for the py-modules directory
COPY --from=py-modules tileserver-utils /py-modules/tileserver-utils

WORKDIR /services/main

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=deps,target=deps \
    uv sync --locked --no-install-project --no-editable --active

# Add source files to project
ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --active

EXPOSE 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.legacy_tileserver:app"]

