DOCKER_IMAGE = macrostrat-api
DOCKER_TAG = latest

.PHONY: build run stop clean

# Get the current version from package.json
VERSION := $(shell node -p "require('./package.json').version")

run:
	docker build -t macrostrat-api .
	docker run --env-file .env --rm -it -p 5000:5000 macrostrat-api

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a v$(VERSION) -m "Version $(VERSION)"
	git push origin tag v$(VERSION)

format:
	# Format the code using Prettier
	yarn run prettier --write .

publish:
	# Ensure the git repository is clean
	@git diff --quiet || (echo "Uncommitted changes present. Please commit or stash them before publishing." && exit 1)
	git tag -a v$(VERSION) -m "Version $(VERSION)"
	git push origin tag v$(VERSION)

