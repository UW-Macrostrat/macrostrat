# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here
FROM python:3.9

# MAPNIK
# Install mapnik for compiling legacy image tiles
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  build-essential software-properties-common curl \
  libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
  libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
  libfreetype-dev libpng-dev libxml2-dev libproj-dev \
  libcairo-dev postgresql-contrib libharfbuzz-dev \
  python-dev git python-setuptools && \
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

# The rest of this (for vector tile generation and the server itself) should be easier.

RUN pip install "poetry==1.1.12" && \
  rm -rf /var/lib/apt/lists/* && \
  poetry config virtualenvs.create false

ENV PIP_DEFAULT_TIMEOUT=100 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/

# Copy only requirements to cache them in docker layer
COPY ./pyproject.toml /app/

RUN poetry install --no-interaction --no-ansi --no-root --no-dev

EXPOSE 8000

# Creating folders, and files for a project:
COPY ./ /app/

# Install the root package
RUN poetry install --no-interaction --no-ansi --no-dev

CMD uvicorn --host 0.0.0.0 --port 8000 macrostrat_tileserver.main:app
