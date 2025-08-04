# Macrostrat command-line interface documentation

Usage: `macrostrat <subcommand> [options]`

## Subcommands

- `db` - Manage the Macrostrat database
- `env` - Manage Macrostrat environments
- `maps` - Manage Macrostrat's maps
- `self` - Inspect the command-line application

...and others yet to be implemented

## Database management

- `macrostrat db dump [database?]`: Create a custom-format dump of the database
- `macrostrat db restore <dumpfile> [database?]`: Restore a database from a
  dumpfile
- `macrostrat db psql [database?]`: Open a psql shell to the database. Also
  supports piping SQL from stdin.
- `macrostrat db update-schema`: run idempotent schema updates

## Environment management

- `macrostrat env`: Switch to another environment

## Map management

The following commands require certain keys to be defined in the
`macrostrat.toml` configuration file. Refer to the [template file in
*map-integration*](../../map-integration/macrostrat.toml.template).

In order to load a new map into Macrostrat, the basic flow is:

- `macrostrat maps pipeline upload-file`:
  *Upload a local archive file for a map to the object store.*

  To add a new map to Macrostrat, or to update an existing one, the first
  step is to upload the required files to the object store.

  This command has two required arguments: a "slug", something that can
  serve as a human-readable identifier for the map, and a path to a local
  archive file, which should be an archive that contains with GIS data.

- `macrostrat maps pipeline ingest-map`:
  *Ingest a map from its already uploaded files*.

  Once the required files for a map have been uploaded to the object store,
  the map can be ingested.

  This command has one required argument: a "slug", the human-readable
  identifier for the map. (Technically, the internal "source ID" can also be
  used.)

In order to load _many_ new maps intos Macrostrat:

- `macrostrat maps pipeline ingest-csv`:
  *Ingest multiple maps from their descriptions in a CSV file.*

  Use the `--help` option to view the documentation for this command.

- `macrostrat maps run-polling-loop`:
  *Poll for and process pending maps.*

  This command will periodically poll Macrostrat's database for "pending
  ingest process" records, which typically indicate that a map has been
  uploaded to Macrostrat's S3 storage via the web application and is ready
  to be processed.

## Kubernetes utilities

- `macrostrat secrets <name>`: Gets a secret in the active Kubernetes namespace
  (if `kube_namespace` is defined in the config)

## Self-inspection

- `macrostrat self`: Inspect the command-line application

## Quickly getting things done

```bash
# Replace a knowledge graph
macrostrat env development
macrostrat db psql -c "DROP SCHEMA macrostrat_kg CASCADE; CREATE SCHEMA macrostrat_kg;"
cat "2024_02_10.sql" | macrostrat db psql
macrostrat db update-schema --subsystems knowledge-graph
```
