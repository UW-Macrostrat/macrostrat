all:
	poetry lock --no-update
	poetry install --only=dev
	macrostrat poetry run mono install
	poetry install

install:
	ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat

format:
	poetry run black .
	poetry run isort .

test:
	poetry run pytest -rP cli/tests

test-warnings:
	poetry run pytest cli/tests -W error
