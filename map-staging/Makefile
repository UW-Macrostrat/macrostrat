# This Makefile is less a build system and more a means of making
# the running of some development tasks more convenient.

.PHONY: all build clean lint reformat

PY_PACKAGE_SRC := macrostrat/
PY_PACKAGE_NAME := macrostrat_map_ingestion

all: reformat lint build

#---------------------------------------------------------------------------

reformat:
	poetry run isort -q $(PY_PACKAGE_SRC)
	poetry run black -q $(PY_PACKAGE_SRC)

lint:
	-poetry run bandit -qr $(PY_PACKAGE_SRC)
	-poetry run mypy $(PY_PACKAGE_SRC)
	-poetry run pylint $(PY_PACKAGE_SRC)

requirements.txt: poetry.lock
	poetry export > requirements.txt

#---------------------------------------------------------------------------

build:
	poetry build

clean:
	rm -rf .mypy_cache/
	rm -rf dist/$(PY_PACKAGE_NAME)-*.tar.gz
	rm -rf dist/$(PY_PACKAGE_NAME)-*.whl
	-rmdir dist/
