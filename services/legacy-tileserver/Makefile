serve:
	poetry run uvicorn macrostrat.legacy_tileserver:app --log-level debug --reload --port 8000

build:
	docker build -t macrostrat-legacy-tileserver .
