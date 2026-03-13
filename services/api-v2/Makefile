DOCKER_IMAGE = macrostrat-api
DOCKER_TAG = latest

.PHONY: build run stop clean

# Get the current version from package.json
VERSION := $(shell node -p "require('./package.json').version")

run:
	docker build -t macrostrat-api .
	docker run --env-file .env --rm -it -p 5000:5000 macrostrat-api

release:
	-git add .
	-git commit -m "deploying"
	git tag -a v$(VERSION) -m "Macrostrat API version $(VERSION)"
	git push origin main --follow-tags

format:
	# Format the code using Prettier
	yarn run prettier --write .
