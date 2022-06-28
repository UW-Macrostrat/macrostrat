# We have to specify a new-ish version of Debian
# to make sure we don't use an out of date image
FROM node:14-bullseye

RUN apt-get -y update && \
    apt-get -y install redis-tools postgresql-client

WORKDIR /code

#COPY ./v1/package.json /code/v1/
COPY ./v2/package.json /code/v2/
COPY ./package.json package.json

RUN npm install
#RUN npm --prefix v1 install
RUN npm --prefix v2 install

# We had to switch to native postgres bindings
# (using the pg-native module) for the purposes
# of building in Docker. I think this is necessary
# to support Postgres v14, but it will make things harder
# to build/run on weird platforms.
# https://github.com/brianc/node-postgres/issues/1508
ENV NODE_PG_FORCE_NATIVE=1

COPY ./ /code/

CMD npm start