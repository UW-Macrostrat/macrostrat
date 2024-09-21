DOCKER_IMAGE = macrostrat-api
DOCKER_TAG = latest

.PHONY: build run stop clean


run:
	docker build -t macrostrat-api .
	docker run --env-file .env --rm -it -p 5000:5000 macrostrat-api


