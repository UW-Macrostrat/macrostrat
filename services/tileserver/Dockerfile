# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here
FROM python:3.10

# MAPNIK
# Install mapnik for compiling legacy image tiles
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        build-essential software-properties-common curl \
        libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
        libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
        libfreetype-dev libpng-dev libxml2-dev libgdal-dev libgeos-dev libproj-dev libcairo-dev \
        libharfbuzz-dev postgresql-contrib && \
    rm -rf /var/lib/apt/lists/*

# Mapnik
ARG MAPNIK_VERSION=4.0.3

WORKDIR /tmp/

RUN git clone --depth 1 --branch v${MAPNIK_VERSION} https://github.com/mapnik/mapnik.git && cd mapnik && git submodule update --init deps
# Install mapnik
WORKDIR /tmp/mapnik
RUN ./configure && make JOBS=4 && make install

ENV BOOST_PYTHON_LIB=boost_python310

# The rest of this (for vector tile generation and the server itself) should be easier.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 POETRY_VIRTUALENVS_CREATE=false

RUN pip install "pip==24.3.1" "setuptools>=75.6.0" "poetry==1.8.4"

# Create and activate our own virtual envrionment so that we can keep
# our application dependencies separate from Poetry's
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /tmp/
# Clone the mapnik python bindings and install them
RUN git clone https://github.com/mapnik/python-mapnik.git && \
    cd python-mapnik && \
    git checkout 10315a6d898ed341f5df5975395f3dc67814ebf6
WORKDIR /tmp/python-mapnik
RUN pip install "pybind11==2.13.6" && pip install .

RUN rm -rf /tmp/*

# Remove build dependencies
RUN apt-get remove -y \
  build-essential software-properties-common \
  libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-python-dev \
  libboost-regex-dev libboost-system-dev libboost-thread-dev libicu-dev libtiff5-dev \
  libfreetype-dev libpng-dev libxml2-dev libproj-dev libgdal-dev libgeos-dev libcairo-dev libharfbuzz-dev

# Software needed to actually run the tileserver

# CartoCSS stylesheet generation
# TODO: we could make this run as a separate step, potentially
# Install nodejs version 20
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs && npm install -g carto

# Install carto
RUN npm install -g carto

WORKDIR /app/

# Copy only requirements to cache them in docker layer
# Right now, Poetry lock file must exist to avoid hanging on dependency resolution
COPY ./deps/timvt/ /app/deps/timvt/
COPY ./pyproject.toml ./poetry.lock /app/

RUN poetry install --no-interaction --no-ansi --no-root --no-dev

EXPOSE 8000

# Creating folders, and files for a project:
COPY ./ /app/

# Install the root package
RUN poetry install --no-interaction --no-ansi --no-dev

CMD uvicorn --host 0.0.0.0 --port 8000 macrostrat_tileserver.main:app
