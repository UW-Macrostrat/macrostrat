all:
	# Install all dependencies
	# Install all optional dependency groups (dev, gis, etc)
	uv sync

gis:
	# Install GIS dependencies
	uv pip install "GDAL==$(shell gdal-config --version)"
	uv sync --group gis

install:
	ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat

format:
	uv run black .
	uv run isort .

test:
	# These tests may fail due to an older GDAL version in use.
	# We need to figure out how to bundle GDAL or run in a Docker context
	uv run macrostrat test all --skip-env -x -s

test-ci:
	# We need a fairly recent version of GDAL (3.10) for map integration tests to pass.
	# For now, we avoid running these tests in CI.
	uv run macrostrat test all --skip-env -x -s -m "not requires_gdal"

test-warnings:
	uv run pytest cli/tests -W error

reset:
	# Remove all virtual environments in subdirectories and re-create the main one
	find . -name ".venv" -type d -exec rm -rf {} +
	make all
