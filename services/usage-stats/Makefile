docker-build:
	docker build -t usage-stats .

docker-run:
	docker run -p 8000:8000 usage-stats

docker:
	docker build -t usage-stats .
	docker run -p 8000:8000 usage-stats

app:
	python3 app.py

install:
	pip install -r requirements.txt