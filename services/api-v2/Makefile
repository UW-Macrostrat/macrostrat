DOCKER_IMAGE = macrostrat-api
DOCKER_TAG = latest

.PHONY: build run stop clean

run:
	docker build -t macrostrat-api .
    docker run --rm -it -p 5550:5550 macrostrat-api


#add env command to docker run
