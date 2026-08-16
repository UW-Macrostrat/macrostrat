FROM imresamu/postgis:15-3.4
# cmake is required to build h3-pg (below); everything else supports pgxn builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential make gcc cmake python3 python3-venv zlib1g-dev \
  postgresql-server-dev-15 build-essential postgresql-15-pgaudit postgresql-15-pgvector \
  && rm -rf /var/lib/apt/lists/*

# h3 is pinned to a specific version, unlike safeupdate: it provides SQL that the
# usage_stats schema depends on, and h3-pg renames functions across major
# versions (4.x `h3_lat_lng_to_cell` is already deprecated in favour of
# `h3_latlng_to_cell`). An unpinned rebuild could therefore break the schema
# months later, so upgrades should be a deliberate edit here.
RUN python3 -m venv /opt/pgxn-venv && \
    /opt/pgxn-venv/bin/pip install pgxnclient && \
    /opt/pgxn-venv/bin/pgxn install safeupdate && \
    /opt/pgxn-venv/bin/pgxn install 'h3=4.5.0'

CMD docker-entrypoint.sh postgres -c shared_preload_libraries=pgaudit
