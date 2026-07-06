# Macrostrat schema management utilities

This module contains utilities for managing Macrostrat's database schema.
It includes tools for dealing with both a stateless, diff-based schema migration
approach and stateful tools for handling specific schema changes that need to occur.

See the [`schema`](https://github.com/UW-Macrostrat/macrostrat/tree/main/schema) directory for more information.

## Composition

The declarative schema is assembled from **chunks** (`macrostrat.core.SchemaDefinition`)
ordered by a dependency graph, rather than by filename:

- `chunks.py` — the explicit list of chunks and their `depends_on` edges. Each
  chunk `provides` a `.sql` directory, a single file, or a function (e.g. the
  colocated `TopologySchema`).
- `composer.py` — `build_schema(db, env, target=…)` topologically sorts and applies
  chunks. `target` is a **subsystem/chunk name**; only that chunk and its
  transitive dependencies are built.
- `test_harness.py` — `DatabaseTestHarness` builds progressively, chunk by chunk,
  skipping already-applied chunks, with an `optimize` transform for fast test builds.

`macrostrat schema graph` lists the chunks and order; `macrostrat schema provision [TARGET]`
builds them.
