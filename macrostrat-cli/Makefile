all:
	poetry lock --no-update
	poetry install

install:
	ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat

test:
	poetry run pytest