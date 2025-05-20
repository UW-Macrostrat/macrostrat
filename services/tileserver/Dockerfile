# From here:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
# NOTE: we might want to make things a bit nicer here
FROM python:3.10

RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  libgdal-dev libproj-dev libgeos-dev && \
  rm -rf /var/lib/apt/lists/*

# The rest of this (for vector tile generation and the server itself) should be easier.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 POETRY_VIRTUALENVS_CREATE=false

RUN python3 -m venv /poetry-env
RUN /poetry-env/bin/pip install -U pip setuptools
RUN /poetry-env/bin/pip install poetry==1.8.4


WORKDIR /app/

# Copy only requirements to cache them in docker layer
# Right now, Poetry lock file must exist to avoid hanging on dependency resolution
COPY ./deps/timvt/ /app/deps/timvt/
COPY ./pyproject.toml ./poetry.lock /app/

# Create and activate our own virtual envrionment so that we can keep
# our application dependencies separate from Poetry's
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Command that always fails
#RUN false

RUN /poetry-env/bin/poetry install --no-interaction --no-ansi --no-root --no-dev

EXPOSE 8000

# Creating folders, and files for a project:
COPY ./ /app/

# Install the root package
RUN /poetry-env/bin/poetry install --no-interaction --no-ansi --no-dev

CMD uvicorn --host 0.0.0.0 --port 8000 macrostrat_tileserver.main:app
