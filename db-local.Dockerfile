FROM postgis/postgis:15-3.4
RUN apt-get update && apt-get install -y --no-install-recommends \
  postgresql-$PG_MAJOR-pgaudit

CMD docker-entrypoint.sh postgres -c shared_preload_libraries=pgaudit
