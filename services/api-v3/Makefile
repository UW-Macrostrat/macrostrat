all:
	poetry lock
	poetry install
	poetry run uvicorn api.app:app \
	    --reload \
	    --log-level debug \
	    --reload-dir ../..

VERSION = $(shell grep -E '^[[:space:]]*version[[:space:]]*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a v$(VERSION) -m "Version $(VERSION)"
	git push origin v$(VERSION)
