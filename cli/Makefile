all:
	poetry lock --no-update
	poetry install

install:
	ln -sf $(shell pwd)/../bin/macrostrat /usr/local/bin/macrostrat

CACHE_DIR := .pytest_cache

profile:
	mkdir -p $(CACHE_DIR)
	poetry run python -m cProfile -o $(CACHE_DIR)/macrostrat-cli.prof -m macrostrat_cli
	poetry run snakeviz $(CACHE_DIR)/macrostrat-cli.prof
