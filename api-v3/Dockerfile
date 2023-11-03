FROM python:3.11

# Setup the Poetry ENV - https://github.com/python-poetry/poetry/issues/525#issuecomment-1227231432
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.6.1
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

#
WORKDIR /code

#
COPY ./poetry.lock ./pyproject.toml /code/

#
RUN poetry update && poetry install

#
COPY ./api /code/api

#
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]