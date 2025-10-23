TAG := hub.opensciencegrid.org/macrostrat/tileserver:$(VERSION)

serve:
	poetry run uvicorn macrostrat_tileserver:app --log-level debug --reload --port 8000

fast:
	poetry run uvicorn macrostrat_tileserver:app --log-level debug --port 8000 --workers 8

test-dev:
	poetry run pytest -s -x --no-drop --skip-legacy-raster

test:
	poetry run pytest -s -x

docker-build:
	docker build -t macrostrat-tileserver .

styles:
	npm install -g carto
	poetry run tileserver create-mapnik-xml mapnik-xml-test

docker-run: 
	docker run -p 8000:8000 --env-file .env macrostrat-tileserver

docker:
	docker build -t macrostrat-tileserver .
	docker run -p 8000:8000 --env-file .env macrostrat-tileserver
VERSION := $(shell node -p "require('./package.json').version")

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a tileserver-v$(VERSION) -m "Version $(VERSION)"
	git push origin tag tileserver-v(VERSION)