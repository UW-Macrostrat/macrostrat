# Macrostrat command-line interface documentation

Usage: `macrostrat <subcommand> [options]`

## Subcommands

- `db` - Manage the Macrostrat database
- `env` - Manage Macrostrat environments
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
