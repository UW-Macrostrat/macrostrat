Schema migration process
========================

## Automated schema migrations

1. Make your desired changes to the schema files located in the `schema/` directory.
2. Run `macrostrat db diff` to generate a diff file that captures the changes made to the schema.
3. Review the generated diff file to ensure it accurately reflects the intended changes.
4. If the automated diff is adequate, run `macrostrat db apply` to apply the migration. Otherwise, manually edit the diff
   file and create a migration file in the `migrations/` directory. This will commonly involve adjusting column types,
   renaming columns, or adding/removing constraints. The new schema does not have to be perfect on the first try.
5. After applying the migration, go to step 2. Repeat until no further changes are needed.

Note: old migraion files in the `migrations/` directory can be deleted once all environments conform to the new schema.

## Manual migrations

Table alterations that cannot be handled by the automated process (e.g., complex data transformations) should
be performed with manually created migration files. To create a manual migration:



# Concepts

- Subsystems ~ named **chunks** of schema (`SchemaDefinition`) with declared `depends_on` edges. A chunk provides a `.sql` directory, a single file, or a function. `core` is decomposed into `public → macrostrat → core` (remainder); finer subsystems can be split out over time.
- Environments ~ different database instances (e.g., development, staging, production) that may be at different schema versions.
- Migrations ~ files that describe changes to the database schema. Not all changes must be made with manual migrations

# Building the schema

The declarative schema is composed from chunks in dependency order (see the
`schema-management` module). To build a subset, name a subsystem as the *target* —
its dependency closure is built:

```
macrostrat schema graph                 # list chunks, deps, and order
macrostrat schema provision             # build the full schema
macrostrat schema provision macrostrat  # build the macrostrat subsystem + deps
```

Tests build schema the same way via `DatabaseTestHarness` (progressively, chunk by chunk).


## Known deficiencies in migration process

Some schema changes are not automatically detected. We hope to improve this in the future:

- Renaming columns
- Inherited foreign keys in partitioned tables
- Inter-schema view dependency cascades
