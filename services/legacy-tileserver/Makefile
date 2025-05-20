serve:
	poetry run uvicorn macrostrat.legacy_tileserver.main:app --log-level debug --reload --port 8000

build:
	docker build -t macrostrat-legacy-tileserver .

styles:
	npm install -g carto
	poetry run tileserver create-mapnik-xml mapnik-xml-test
