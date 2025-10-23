VERSION = $(shell grep -E '^[[:space:]]*version[[:space:]]*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')


all:
	docker build -t tileserver .
	docker run tileserver

serve:
	poetry run uvicorn macrostrat.legacy_tileserver:app --log-level debug --reload --port 8000

build:
	docker build -t macrostrat-legacy-tileserver .

whl:
		bash ./scripts/prepare-services

release:
	# Ensure that the repository is clean
	git diff-index --quiet HEAD --
	git tag -a legacy-tileserver-v$(VERSION) -m "Version $(VERSION)"
	git push origin legacy-tileserver-v$(VERSION)
