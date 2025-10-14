all:
	poetry lock
	poetry install
	poetry run uvicorn api.app:app \
	    --reload \
	    --log-level debug \
	    --reload-dir ../..

# Modify reload directory to pull in changes from shared code
