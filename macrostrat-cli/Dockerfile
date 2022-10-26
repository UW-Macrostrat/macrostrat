FROM python:3.10

WORKDIR /code

RUN pip install "poetry==1.2.2"

COPY poetry.lock pyproject.toml /code/

RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

COPY ./ /code/

RUN poetry install --no-interaction --no-ansi

ENTRYPOINT ["macrostrat"]