# Map packages

Maps are compiled in several places — locally, in development — and need to
reach production. A **map package** carries one or more maps between any two
Macrostrat databases: a GeoPackage holding each map with everything that
describes it, keyed by slug rather than by the database-specific ids that differ
between environments.

```sh
# One map, a set by slug pattern, or a whole compilation tree
macrostrat maps export ashibe.gpkg japan_ashibe
macrostrat maps export japan.gpkg 'japan_*' --exclude 'japan_test*'
macrostrat maps export ngs.gpkg --compilation ngs

# In the target environment
macrostrat maps ingest ngs.gpkg
macrostrat maps ingest 'ngs-arizona*' ngs.gpkg   # only matching slugs
```

`macrostrat maps ingest` recognises a package by its contents, not its name, and
takes this branch instead of the usual GIS-file ingest. The previous
`macrostrat maps export` (a region export of carto layers by bbox or WKT) is now
`macrostrat maps export-region`.

## What a package holds

| Layer                      | From                                | Notes                                                            |
| -------------------------- | ----------------------------------- | ---------------------------------------------------------------- |
| `maps_sources`             | `maps.sources`                      | `superseded_by` travels as `superseded_by_slug`                  |
| `polygons`, `lines`, `points` | `maps.*`                         | Materialized compilations' polygons come after their members'    |
| `legend`, `map_legend`     | `maps.legend`, `maps.map_legend`    | Included, but processing rebuilds them                           |
| `ingest_process`, `ingest_process_tag` | `maps_metadata.*`       |                                                                  |
| `map_area`, `boundary_op`  | `map_bounds.*`                      | The authored boundary and its operations; recorded in the target's own barrier layer on import |
| `compilation`, `compilation_member` | `map_bounds.*`             | Edges touching an exported map, with both ends as slugs          |
| `sources__<table>`         | `sources.<table>`                   | Staging tables; omit with `--no-sources-schema`                  |

A **compilation tree** (`--compilation ngs`) is the compilation and every map
beneath it at any depth (`map_bounds.members_of(id, true)`). Registered map
layers (`tiny` … `carto-large`) are never exported — every database seeds its
own — but edges to them are, so a map's layer placement survives the trip.

**Staging tables** are found under each map's slug and recorded
`primary_table` / `primary_line_table`, under each exported compilation's slug,
and under `--staging-prefix`. A table named for a map is *owned* by it; a shared
one (NGS stages its members into `sources.ngs_*`) contributes only the exported
maps' rows.

**Not exported**: topology state (topogeometries, `map_face`, `map_priority`,
`map_topo`, `geometry_hash`), `compilation.member_hash`, and match tables
(`legend_liths`, `legend_strat_names`, `map_units`, …). All are derived and are
rebuilt in the target.

### Format

Three attribute tables make the file self-describing: `macrostrat_package`
(key/value metadata; `format = macrostrat-map-package`, `format_version`),
`macrostrat_package_layers` (source table, geometry column, SRID, row count and
staging owner per layer), and `macrostrat_package_columns` (every column's
Postgres type). Integers, floats, booleans and text are stored natively, so the
layers open in QGIS. Every other type — arrays, `jsonb`, enums, timestamps,
secondary geometry columns — is stored as its Postgres text form and cast back
on import. Geometry types are preserved exactly (no promotion to multi-part).

## What an import does

**Conflicts are settled first.** For each slug already in the target, the
import asks whether to overwrite, skip, overwrite all, skip all, or stop — all
before anything is written, so stopping leaves the target untouched. Without a
terminal, pass `--on-conflict overwrite|skip|stop`.

**Ids are the target's.** Every `source_id`, `map_id`, `legend_id`, `line_id`
and `point_id` is drawn from the target's own sequences, and the package's
references are rewritten to match: legend links, staging `source_id`s, the
`orig_id`s by which a derived compilation's polygons name their members', and
compilation edges resolved by slug.

**Overwriting is in place.** An overwritten map keeps its target `source_id`
and `maps.sources` row, so what refers to it from outside the package (carto
tables, faces, compilations the package doesn't know about) stays valid. Its
features and legend are replaced, along with rows keyed on its old polygons
(`map_liths`, `map_units`, `lookup_*`). Its boundary operations, tags and the
membership *of* it as a compilation are replaced where the package carries
them. `ingest_process` and `map_area` are upserted, which keeps the target's
`map_files` links and topology references; a changed boundary clears
`geometry_hash`, so the next topology update re-nodes it. Its own placements in
other compilations are added to, never removed. A staging table the map owns is
recreated; its rows in a shared table are replaced.

**It is one transaction, and resilient.** The map itself — `maps.sources`,
features, legend — loads or nothing does. Everything else may be stale or may
not fit the target's schema, so each such table loads under its own savepoint
and falls back to row-by-row, reporting what it dropped. An ingest state the
target doesn't define is left empty rather than losing the process record; a
package column the target lacks is dropped with a warning; a compilation edge
the target rejects (a cycle, say) is skipped alone. Each imported map gets an
`import-package` entry in `maps.source_operations` recording where it came from.

**Then process.** Legends and topology are derived, so finish with
`macrostrat maps process` on the imported maps and `macrostrat topo update`.

The import is a data write, gated like any other (see
[Environment configuration and write safety](Environment%20configuration%20and%20write%20safety.md)).

## Patching existing maps

`ingest` creates or replaces whole maps. To carry only *parts* of maps that
already exist in the target — corrected metadata, edited boundary operations —
export just those elements and apply them with `patch`:

```sh
macrostrat maps export spain-ops.gpkg spain --element boundary-ops
macrostrat maps patch spain-ops.gpkg --dry-run   # show the plan
macrostrat maps patch spain-ops.gpkg             # show it, then ask once
```

| Element        | Merge                                                                 |
| -------------- | --------------------------------------------------------------------- |
| `metadata`     | Descriptive `maps.sources` fields (name, authors, ref, url, license, keywords, …), field by field. A field the package leaves empty keeps the target's value |
| `boundary-ops` | The map's whole operation stack is replaced, then its bounds rebuilt  |

Maps are matched by slug and **never created**; a slug the target lacks is
listed and skipped. The plan shows each map's changes — changed fields, and the
old and new stacks as a diff — and is applied all or nothing once approved
(`--yes` approves it without asking). Patch elements narrow with `--element`
and maps with slug globs. Each patched map gets a `patch-package` entry in
`maps.source_operations`.

A computed opening's cached geometry (`union`, `compile`, `world`) describes
the environment it was computed in, so it isn't compared and doesn't travel:
the target keeps its own cache when the opening is unchanged, and recomputes it
from its own features otherwise. Finish with `macrostrat topo update` to node
the changed boundaries.

A package exported with `--element` is **partial** (format version 2, listing
its `elements`); `ingest` refuses it. `patch` also accepts a whole package and
applies every element it carries.

## From Python

The library functions take a database, as elsewhere in `map-integration`:

```python
from macrostrat.map_integration.package import (
    ConflictAction,
    export_maps,
    import_package,
)

export_maps(db, "ngs.gpkg", maps, staging_prefixes={"ngs"})
report = import_package(other_db, "ngs.gpkg", on_conflict=ConflictAction.skip)
report.imported, report.warnings

from macrostrat.map_integration.package.patch import apply_patch, plan_patch

plan = plan_patch(other_db, "spain-ops.gpkg")
plan.changes, plan.missing
apply_patch(other_db, plan)
```
