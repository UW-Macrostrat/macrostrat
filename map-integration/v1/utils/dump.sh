pg_dump -C --clean --no-owner -T sources.etopo1 -U john -h localhost -p 5432 burwell | gzip > $(date +"%Y.%m.%d").burwell.sql.gz

pg_dump --clean --table sources.etopo1 -U john -h localhost -p 5432 burwell > $(date +"%Y.%m.%d").etopo1.sql
sed -i.bak -e 's/search_path = sources/search_path = public, sources/g' $(date +"%Y.%m.%d").etopo1.sql
sed -i.bak -e 's/CREATE TABLE etopo1/CREATE TABLE sources.etopo1/g' $(date +"%Y.%m.%d").etopo1.sql

gzip $(date +"%Y.%m.%d").etopo1.sql
rm $(date +"%Y.%m.%d").etopo1.sql.bak
