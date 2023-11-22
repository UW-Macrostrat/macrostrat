all: install

.PHONY: install init update_functions test dev features

lock:
	bin/update-packages

install:
	make lock
	poetry install

init:
	-createdb plate-rotations
	poetry run corelle init --drop
	poetry run bin/load-models

update_functions:
	cat py-packages/engine/corelle/engine/schema/*-functions.sql | psql plate-rotations

baseurl := https://raw.githubusercontent.com/martynafford/natural-earth-geojson/master

features: bin/load-features
	poetry run bin/load-features --redo plate-rotations

test:
	poetry run bin/run-tests

dev:
	cd frontend && poetry run npm run dev
