DOCKER_IMAGE = macrostrat-api
DOCKER_TAG = latest

.PHONY: build run stop clean

# Get the current version from package.json
VER := $(shell node -p "require('./package.json').version")

run:
	docker build -t macrostrat-api .
	docker run --env-file .env --rm -it -p 5000:5000 macrostrat-api

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a v$(VER) -m "Version $(VER)"
	git push origin v$(VER)

