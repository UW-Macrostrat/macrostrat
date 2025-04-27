# We have to specify a new-ish version of Debian
# to make sure we don't use an out of date image
FROM node:20-bullseye

RUN apt-get -y update && \
    apt-get -y install redis-tools postgresql-client && \
    apt-get -y install ca-certificates supervisor

WORKDIR /code

COPY ./package.json ./yarn.lock ./code/

RUN yarn install

# We had to switch to native postgres bindings
# (using the pg-native module) for the purposes
# of building in Docker. I think this is necessary
# to support Postgres v14, but it will make things harder
# to build/run on weird platforms.
# https://github.com/brianc/node-postgres/issues/1508
ENV NODE_PG_FORCE_NATIVE=1

COPY ./ /code/

COPY ./supervisor/api.conf /etc/supervisor/conf.d/
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"]
