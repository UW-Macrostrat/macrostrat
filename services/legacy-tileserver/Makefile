all:
	docker build -t tileserver .
	docker run tileserver

serve:
	poetry run uvicorn macrostrat.legacy_tileserver:app --log-level debug --reload --port 8000

build:
	docker build -t macrostrat-legacy-tileserver .

whl:
		bash ./scripts/prepare-services

VERSION := $(shell node -p "require('./package.json').version")

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a $(VERSION) -m "Version $(VERSION)"
	git push origin tag $(VERSION)

