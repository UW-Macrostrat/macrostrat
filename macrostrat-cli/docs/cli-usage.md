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

## Self-inspection

- `macrostrat self`: Inspect the command-line application
