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

- Subsystems ~ named **chunks** of schema (`SchemaDefinition`) with declared `depends_on` edges. A chunk provides a
  `.sql` directory, a single file, or a function. `core` is decomposed into `public → macrostrat → core` (remainder);
  finer subsystems can be split out over time.
- Environments ~ different database instances (e.g., development, staging, production) that may be at different schema
  versions.
- Migrations ~ files that describe changes to the database schema. Not all changes must be made with manual migrations

# Building the schema

The declarative schema is composed from chunks in dependency order (see the
`schema-management` module). To build a subset, name a subsystem as the *target* —
its dependency closure is built:

```
macrostrat schema graph                     # list chunks, deps, and order
macrostrat schema provision                 # build the full schema
macrostrat schema provision --target macrostrat   # subsystem + its dependencies
macrostrat schema sync                      # re-apply views, procedures, and grants
macrostrat schema sync --target maps --no-dependents   # just one subsystem's
```

`--target` / `--no-dependents` are a shared option block (used by both `provision` and
`sync`). Tests build schema the same way via `DatabaseTestHarness` (progressively, chunk by chunk).

# Direction

We are in the process of reorienting the schema around modular **subsystem chunks** (see the
`schema-management` module). Today `core` is only coarsely split (`public → macrostrat → core`), the `.sql` still
lives centrally in this directory, and stateful migrations are a separate system.
The intent is to:

- Colocate each subsystem's SQL with its owning code (as `map-topology`
  already does), discovering chunks rather than listing them centrally;
- Decompose `core` into finer named subsystems (`maps`, `tiles`, …); and
- Fold migrations into the same dependency graph, so a subsystem's structure,
  transitions, and seed data live together.

Until then, add new `.sql` here — it lands in the `core` chunk by default.

## Known deficiencies in migration process

Some schema changes are not automatically detected. We hope to improve this in the future:

- Renaming columns
- Inherited foreign keys in partitioned tables
- Inter-schema view dependency cascades
