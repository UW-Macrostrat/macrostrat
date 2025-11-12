all:
	# Install all dependencies
	uv sync --all-groups # Install all optional dependency groups (dev, gis, etc)

install:
	ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat

format:
	poetry run black .
	poetry run isort .

test:
	# These tests may fail due to an older GDAL version in use.
	# We need to figure out how to bundle GDAL or run in a Docker context
	uv run macrostrat test all --skip-env -x -s
	#	poetry run pytest -s -x \
	#		--ignore=runtime-tests \
	#		--ignore=services \
	#		--ignore=v2-transition \
	#		--ignore=submodules \
	#		--skip-env \
	#		.

test-ci:
	# We need a fairly recent version of GDAL (3.10) for map integration tests to pass.
	# For now, we avoid running these tests in CI.
	uv run macrostrat test all --skip-env -x -s -m "not requires_gdal"

test-warnings:
	uv run pytest cli/tests -W error
