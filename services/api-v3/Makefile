all:
	poetry lock
	poetry install
	poetry run uvicorn api.app:app \
	    --reload \
	    --log-level debug \
	    --reload-dir ../..
VERSION := $(shell node -p "require('./pyproject.toml').version")

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a v$(VERSION) -m "Version $(VERSION)"
	git push origin tag v$(VERSION)
# Modify reload directory to pull in changes from shared code
