# Command note:
#   `macrostrat up [CONTAINER]`  - build + start the whole stack (or ONE container)
#                                  and FOLLOW LOGS in the foreground (no -d).
#   `macrostrat down`            - stop + remove ALL services.
#   `macrostrat restart [CONT]`  - restart (+follow logs).
#   `macrostrat compose ...`     - raw `docker compose` passthrough; use this when you
#                                  need -d, a subset of services, exec, ps, etc.
# Prefer `macrostrat up`/`down` for full-stack lifecycle; `compose` for partial control.

all:
	# Install all dependencies
	# Install all optional dependency groups (dev, gis, etc)
	uv sync
	uv add "psycopg[binary]"

start-database:
	macrostrat compose up -d database storage

start-gateway:
	macrostrat up gateway

build-restart:
	macrostrat up --force-recreate api_v3

start-services:
	macrostrat --verbose up
stop-services:
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

