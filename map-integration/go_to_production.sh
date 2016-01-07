ssh -p 2200 -f -N -M -S /tmp/tmp-sock -L 5440:127.0.0.1:5432 jczaplewski@strata.geology.wisc.edu

dropdb -U john -h localhost -p 5440 burwell_new
createdb -U john -h localhost -p 5440 burwell_new

pg_dump --no-owner -T sources.etopo1 -U john -h localhost -p 5432 burwell | psql -U john -h localhost -p 5440 burwell_new

pg_dump --clean --table sources.etopo1 -U john -h localhost -p 5432 burwell > etopo1.sql
sed -i.bak -e 's/search_path = sources/search_path = public, sources/g' etopo1.sql
sed -i.bak -e 's/CREATE TABLE etopo1/CREATE TABLE sources.etopo1/g' etopo1.sql

psql -U john -h localhost -p 5440 burwell_new < etopo1.sql

rm etopo1.sql

ssh -S /tmp/tmp-sock -O exit jczaplewski@strata.geology.wisc.edu

: <<'END'
psql -U john -c "ALTER DATABASE burwell RENAME TO burwell_old"
psql -U john -c "ALTER DATABASE burwell_new RENAME TO burwell"

SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'burwell' AND pid <> pg_backend_pid();

END
