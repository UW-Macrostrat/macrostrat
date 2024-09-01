all:
	macrostrat poetry lock --no-update
	macrostrat poetry install --only=dev
	macrostrat poetry run mono install
	macrostrat poetry install

install:
	ln -sf $(shell pwd)/macrostrat /usr/local/bin/macrostrat
