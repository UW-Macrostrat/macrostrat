all:
	poetry lock --no-update
	poetry install --only=dev
	macrostrat poetry run mono install
	poetry install

install:
	cli/macrostrat install

format:
	poetry run black .
	poetry run isort .

test:
	poetry run pytest cli
