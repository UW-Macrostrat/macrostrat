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

- `macrostrat maps ingest-file`:
  *Ingest a local file containing a map into Macrostrat*.

  This command has two required arguments: a path to a local file, which
  should be an archive containing GIS data, and a "slug", which should be
  a short string that can be used as a human-readable identifier for the
  map.

  This command will upload the archive to S3 and then attempt to locate
  files containing GIS data, which will be used to populate database tables
  with lines, points, and polygons.

  This command also has numerous optional arguments, which can be listed
  using the `--help` option. These arguments can be used to describe the
  report that the map is a part of and to provide alternative configuration
  values for where in S3 to upload the archive to.

- `macrostrat maps ingest-object`:
  *Ingest an object in S3 containing a map into Macrostrat.*

  This command has two required arguments: the bucket and key for an object
  in Macrostrat's S3 storage.

  This command will download the object from S3 and process it in a similar
  manner to the `ingest-file` command. (Technically, `ingest-file` actually
  relies on this command to do much of its work.)

  The typical use for this command is to trigger the processing of a map
  that has been uploaded to Macrostrat's S3 storage via the web application.

- `macrostrat maps run-polling-loop`:
  *Poll for and process pending ingest processes.*

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
