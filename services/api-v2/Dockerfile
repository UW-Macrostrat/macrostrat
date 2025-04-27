# We have to specify a new-ish version of Debian
# to make sure we don't use an out of date image
FROM node:20-bullseye

RUN apt-get -y update && \
    apt-get -y install redis-tools postgresql-client && \
    apt-get -y install ca-certificates supervisor

WORKDIR /code

COPY package.json yarn.lock .yarnrc.yml /code/
COPY .yarn/releases /code/.yarn/releases

RUN yarn install

COPY ./ /code/

COPY ./supervisor/api.conf /etc/supervisor/conf.d/
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"]
