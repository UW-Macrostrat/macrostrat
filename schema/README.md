Schema migration process
========================

1. Make your desired changes to the schema files located in the `schema/` directory.
2. Run `macrostrat db diff` to generate a diff file that captures the changes made to the schema.
3. Review the generated diff file to ensure it accurately reflects the intended changes.
4. If the automated diff is adequate, run `macrostrat db apply` to apply the migration. Otherwise, manually edit the diff
   file and create a migration file in the `migrations/` directory. This will commonly involve adjusting column types,
   renaming columns, or adding/removing constraints. The new schema does not have to be perfect on the first try.
5. After applying the migration, go to step 2. Repeat until no further changes are needed.

Note: old migraion files in the `migrations/` directory can be deleted once all environments conform to the new schema.
