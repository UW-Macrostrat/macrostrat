all:
	poetry lock
	poetry install
	poetry run uvicorn api.app:app \
	    --reload \
	    --log-level debug \
	    --reload-dir ../..
# Extract project name (api-v3) from pyproject.toml
NAME = api-v3

# Extract version (2.3.2) from pyproject.toml
VERSION = $(shell grep -E '^[[:space:]]*version[[:space:]]*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')

# Final tag: api-v3-v2.3.2
TAG = $(NAME)-v$(VERSION)

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a $(TAG) -m "Version $(TAG)"
	git push origin $(TAG)