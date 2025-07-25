docker-build:
	docker build -t usage-stats .

docker-run:
	docker run -p 8000:8000 usage-stats

docker:
	docker build -t usage-stats .
	docker run -p 8000:8000 usage-stats

worker:
	python3 worker.py

install:
	pip install -r requirements.txt