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

# The rest of this (for vector tile generation and the server itself) should be easier.


RUN pip install --no-cache-dir "pip==25.1.1" && pip install --no-cache-dir "poetry==2.1.1"


# Copy only requirements to cache them in docker layer
# Right now, Poetry lock file must exist to avoid hanging on dependency resolution
COPY ./pyproject.toml ./poetry.lock /app/

# Create and activate our own virtual envrionment so that we can keep
# our application dependencies separate from Poetry's

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --without dev --without local

# This gets locally built deps, which must be staged in the
# image directory before building. This is breakable and we'd like
# to end up with a better solution eventually.
COPY ./deps/ /app/deps/

# Install local wheels without caring about hashes (poetry gets mad if package hashes don't match.)
RUN pip install --no-cache-dir ./deps/*.whl

# Creating folders, and files for a project:
COPY ./ /app/

# Install the root package
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev

EXPOSE 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.legacy_tileserver:app"]

