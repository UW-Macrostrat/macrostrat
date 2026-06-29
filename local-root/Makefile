all:
	# Install all dependencies
	# Install all optional dependency groups (dev, gis, etc)
	uv sync
	uv add "psycopg[binary]"

start-database:
	# Install GIS dependencies
	#uv pip install "GDAL==$(shell gdal-config --version)"
	macrostrat compose up -d database storage

start-gateway:
	macrostrat compose up -d gateway

build-restart:
	macrostrat compose up -d --build --force-recreate

start-services:
	macrostrat compose up -d gateway postgrest api_v2 api_v3 tileserver_core tileserver_legacy tileserver_cache
stop-services:
	#macrostrat compose stop postgrest api_v3 tileserver_core tileserver_legacy tileserver_cache gateway
	macrostrat compose stop postgrest api_v2 api_v3 tileserver_core tileserver_legacy tileserver_cache gateway
stop-gateway:
	macrostrat compose stop gateway
test:
	macrostrat compose exec database psql -U macrostrat_admin -d macrostrat
	macrostrat compose ps
	macrostrat compose exec database psql -U macrostrat_admin -d macrostrat \
  	-c "select count(*) from maps.sources;"
next-steps:
	#database role mapping
	macrostrat db config # https://github.com/UW-Macrostrat/macrostrat/blob/main/schema/core/0000-roles.sql
	macrostrat schema #document these processes...

