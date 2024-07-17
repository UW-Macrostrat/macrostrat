FROM dimitri/pgloader:latest
RUN apt-get update && apt-get install -y postgresql-client
RUN apt-get install -y ca-certificates
WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt
CMD ["python3", "app.py"]
