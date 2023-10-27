serve:
	poetry run uvicorn macrostrat_tileserver.main:app --log-level debug --reload --port 8000

test:
	strat compose run tileserver pytest