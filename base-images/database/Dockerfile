FROM imresamu/postgis:15-3.4
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential make gcc python3 python3-venv zlib1g-dev \
  postgresql-server-dev-15 build-essential postgresql-15-pgaudit postgresql-15-pgvector \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/pgxn-venv && \
    /opt/pgxn-venv/bin/pip install pgxnclient && \
    /opt/pgxn-venv/bin/pgxn install safeupdate

CMD docker-entrypoint.sh postgres -c shared_preload_libraries=pgaudit
