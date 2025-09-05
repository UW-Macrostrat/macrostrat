all:
	poetry lock
	poetry install --with=dev,gis
	# This breaks on fresh installs, not sure
	#./bin/macrostrat poetry run mono install
	# Install the version of the GDAL bindings that matches the native lib.
	# This is breakable and should be replaced with a more robust solution.
	poetry run pip install GDAL==$(shell gdal-config --version | sed 's/\([0-9]*\)\.\([0-9]*\).*/\1.\2/')

install:
	ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat

format:
	poetry run black .
	poetry run isort .

test:
	# These tests may fail due to an older GDAL version in use.
	# We need to figure out how to bundle GDAL or run in a Docker context
	poetry run macrostrat test all --skip-env -x -s
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
	poetry run macrostrat test all --skip-env -x -s -m "not requires_gdal"

test-warnings:
	poetry run pytest cli/tests -W error
