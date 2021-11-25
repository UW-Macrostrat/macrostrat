FROM node:14

RUN apt-get update && \
    apt-get -y install redis-tools && \
    apt-get -y install postgresql-client

WORKDIR /code

COPY ./v1/package.json /code/v1/
COPY ./v2/package.json /code/v2/
COPY ./package.json package.json

RUN npm install
RUN npm --prefix v1 install
RUN npm --prefix v2 install

COPY ./ /code/

CMD npm start