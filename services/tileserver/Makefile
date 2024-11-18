serve:
    poetry run uvicorn macrostrat_tileserver.main:app --host localhost --port 8000 --reload

fast:
	poetry run uvicorn macrostrat_tileserver.main:app --log-level debug --port 8000 --workers 8

test:
	strat compose run tileserver pytest