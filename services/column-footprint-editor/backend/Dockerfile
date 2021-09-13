FROM python:3.9.5

COPY ./requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /app
WORKDIR /app

COPY ./ /app/

EXPOSE 8000

COPY . .
CMD ["python3", "__init__.py"]