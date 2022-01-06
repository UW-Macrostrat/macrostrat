## Stratigraphic Column Infrastructure

This repository is firstly the home of the successor to [Dacite](), a php application for collecting
stratigraphic column data. This new app will be built off of and feed data directly into a postgres instance
of burwell (modified and smaller). Currently it only holds the macrostrat schema with altered tables to
enforce FOREIGN KEY constraints. **NOTE**: there were some conflicts on alter tables and some rows needed to be deleted. Many were minor deletions (with one exception) of linking tables. Notes on how much was deleted
and from which tables can be found in `db-alterations/add-foreign-keys.sql`.

Locally, the process can be recreated using the `dump-burwell` script in `bin`.
