# Macrostrat local installation

This is the root for running Macrostrat locally.

## Installation

- Install Docker and the Macrostrat command-line application
- Create a basic configuration file

## Create a basic configuration file

_More information coming soon_

### Set the password for the database superuser

This is a chicken-and-egg problem currently

```sh
macrostrat db psql -c "ALTER USER macrostrat_admin WITH PASSWORD '<info>';"
```

### Create the database

The Macrostrat database currently cannot be created from scratch.
You can load a database dump as such:

```sh
macrostrat db restore <dump-file>
```
