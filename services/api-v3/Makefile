all:
	uv sync
	uv run uvicorn api.app:app \
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
	uv sync
	git add .
	git commit -m "deploying"
	git tag -a $(TAG) -m "Version $(TAG)"
	git push origin main --follow-tags


test-fieldsite:
	uv run pytest -q \
  	--confcutdir=api/tests \
  	api/tests/test_fieldsite.py

test-object:
	uv run pytest -q \
  	--confcutdir=api/tests \
  	api/tests/test_object.py



