# Dockerfile for the corelle API server
FROM python:3.10

WORKDIR /code

RUN apt-get -y update && apt-get -y install postgresql-client

RUN pip install poetry==1.4.0

COPY ./poetry.lock ./pyproject.toml /code/

RUN poetry install --no-root

COPY ./macrostrat /code/macrostrat

RUN poetry install

EXPOSE 8000

CMD poetry run uvicorn --host 0.0.0.0 --port 8000 --proxy-headers macrostrat.structure_api:app
