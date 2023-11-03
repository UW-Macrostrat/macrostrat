all:
	poetry lock --no-update
	poetry install --only=dev
	poetry run mono install
	poetry install

install:
	ln -sf $(shell pwd)/macrostrat /usr/local/bin/macrostrat