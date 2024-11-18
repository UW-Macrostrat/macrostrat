serve:
    poetry run uvicorn macrostrat_tileserver.main:app --host 0.0.0.0 --port 8000

fast:
	poetry run uvicorn macrostrat_tileserver.main:app --log-level debug --port 8000 --workers 8

test:
	strat compose run tileserver pytest