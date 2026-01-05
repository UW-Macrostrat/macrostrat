all:
	python gems_etl.py

install:
	python -m venv venv && source venv/bin/activate
	pip install pipreqs
	pipreqs . --force
	pip install -r requirements.txt



