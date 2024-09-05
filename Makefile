all:
	poetry --directory cli lock --no-update
	poetry --directory cli install --only=dev
	cd cli && macrostrat poetry run mono install
	poetry --directory cli install

install:
	cli/macrostrat install
