all:
	docker build -t tileserver .
	docker run tileserver

serve:
	poetry run uvicorn macrostrat.legacy_tileserver:app --log-level debug --reload --port 8000

build:
	docker build -t macrostrat-legacy-tileserver .

whl:
		bash ./scripts/prepare-services

