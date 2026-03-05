## Current state (Phase 2.5) — What is implemented and working

* **dynamic schema introspection** (Postgres)
* **declarative field mapping** (`macrostrat_mapping.json`)
* **pluggable per-entity logic** (Python handlers/plugins for non-generic logic)

### Files (Phase 2.5)

1. **`ingest_macrostrat.py`** (Phase 2.5 final, no globals)
2. **`macrostrat_mapping.json`** (Phase 2.5, `mapping_version: "2.5"`)

Excel requirement: `metadata` tab must include:

* `project_id` (integer)
* `mapping_version` = `"2.5"` (must match the JSON mapping file)

### Execution flow when the script runs

1. **Read mapping JSON** and select Excel filename (default `macrostrat_import.xlsx` unless overridden).
2. **Read Excel workbook** using `openpyxl` and **trim whitespace** from all string cells (headers and values) at load time.
3. **Mapping version enforcement**: fail fast if Excel `metadata.mapping_version` != JSON `mapping_version`.
4. **Extract `project_id`** from `metadata` tab and validate integer.
5. **Verify project exists**:

   * Macrostrat API: `https://macrostrat.org/api/defs/projects?project_id=...`

     * expected JSON shape: `{"success": {"data": [{"project_id": <int>, "project": <str>, ...}]}}`
     * confirm returned `project_id` matches
   * Local Postgres: confirm `project_id` exists in `macrostrat.projects.id`
6. **Introspect DB schema** via `information_schema.columns`:

   * validate mapping fields exist on each mapped table
   * validate any mapped `NOT NULL`/no default columns have a mapping source/default
   * **Phase 2.5 guardrail**: for `macrostrat.cols` specifically, enforce that **all** `NOT NULL`/no-default columns are covered by mapping (or have DB defaults). This catches DB schema evolution before ingest begins.
7. Begin a **single transaction** (commit on success, rollback on any failure).
8. **Ingest refs** (mapping-driven, idempotent):

   * Read `refs` sheet (header row required).
   * Required Excel fields:

     * `ref_id` unique in sheet
     * integer `date`
     * non-empty `title`
     * non-empty `authors` (or `author`)
   * Mapping to `macrostrat.refs`:

     * `pub_year` ← `date`
     * `author` ← `authors` or `author`
     * `ref` ← concat_ws('. ', title, publication) via mapping expr
     * `doi` ← `doi` (nullable)
     * `compilation_code` ← `compilation` default `""` (NOT NULL)
     * `url` ← `url` (nullable)
   * Idempotency / natural key select-insert:

     * natural key: (`pub_year`, `author`, `ref`)
     * if found: reuse existing id
     * else: insert and return id
   * Output: `ref_map` of Excel `ref_id` → DB `refs.id`
9. **Ingest col_groups** (mapping-driven, idempotent without relying on DB constraints):

   * Read `columns` sheet and take distinct `col_group`.
   * Insert/select into `macrostrat.col_groups` with:

     * `project_id`
     * `col_group_long`
     * `col_group`
   * Natural key: (`project_id`, `col_group_long`)
   * Output: `col_groups_map` of `col_group` → DB `col_groups.id`
10. **Ingest columns** (hybrid: plugin logic + mapping-driven insert for `macrostrat.cols`):

* Read `columns` sheet and validate:

  * required columns exist in header: `col_id`, `col_name`, `col_group`, `ref_ids`, `col_type`
  * per-row required:

    * unique `col_id` in sheet
    * non-empty `col_name`, `col_group`
    * `col_type` ∈ {`column`, `section`} (lowercased)
    * `ref_ids` is 1+ comma-separated ids that exist in `refs` sheet (via `ref_map`)
    * **either** decimal `lat`+`lng` **or** valid WKT polygon `geom` (exclusive)
  * sheet-level uniqueness:

    * `(col_name, col_group)` unique
    * `(lat,lng)` unique among lat/lng rows
    * `geom` WKT unique among polygon rows
* WKT polygons validated in DB using PostGIS: `ST_IsValid` and `GeometryType` ∈ {POLYGON, MULTIPOLYGON}.
* **Idempotent get-or-create for `macrostrat.cols`**:

  * Existence check key includes:

    * `project_id`, `col_group_id`, `col_name`, `col_type`, `status_code` **and**
    * geometry branch:

      * if polygon: `ST_Equals(poly_geom, ST_GeomFromText(wkt, 4326))`
      * else: `lat`, `lng`, and `poly_geom IS NULL`
  * If found: reuse existing `cols.id`
  * Else: insert new `cols` row **using mapping-driven field list** with plugin handlers:

    * `project_id` constant
    * `col_group_id` from `col_groups_map`
    * `status_code` constant `"in process"`
    * `col_type` from Excel `col_type` lowercased
    * `col_name` from Excel
    * `created` SQL `now()`
    * `col`:

      * use Excel `col` if present and numeric
      * else use numeric conversion of `col_id` if safe for numeric(6,2)
      * else generate sequential integers (as numeric(6,2))
    * `col_position` set to `""` (NOT NULL)
    * `lat`, `lng`, `coordinate`:

      * if lat/lng: set from decimals, coordinate = point(lng,lat)
      * if polygon: compute point-on-surface centroid for lat/lng and coordinate via PostGIS expressions
    * `poly_geom`:

      * if polygon: `ST_GeomFromText(wkt,4326)`
      * else omitted via `omit_if_none`
    * `col_area` (double precision NOT NULL):

      * if polygon: computed geodesic area in km²: `ST_Area(geom::geography)/1e6`
      * if lat/lng: `0.0`
* Output: `col_map` of Excel `col_id` → DB `cols.id`

11. **Insert join rows**:

* `macrostrat.col_refs`:

  * for each column row, insert one row per referenced `ref_id`
  * `ON CONFLICT DO NOTHING` ensures idempotency (duplicates skipped)
* `macrostrat.col_areas`:

  * only for polygon columns:

    * insert one row per `cols.id` if none exists
    * fields: `col_id`, `wkt` (original), `col_area` (geometry column) = `ST_GeomFromText(wkt,4326)`, `gmap` = `""`

12. Print console summaries for refs, col_groups, columns, and report success.
13. Commit transaction on success; rollback on any failure.

### Confirmed tests

* Importing an Excel file whose data are already present results in **reused** reporting and **no new inserts**.
* Importing new data inserts correctly while maintaining idempotency on rerun.
* Last cleanup removed all global state (no `context_global`), passing `cols_entity` and `cols_handlers` explicitly into the columns ingest function.

---

## Phase 3 plan (units ingestion)

### Overall approach

Use the same architecture as Phase 2.5:

* **mapping-driven field lists** for each target table
* **schema introspection guardrails**

  * mapped fields exist
  * mapped NOT NULL/no-default satisfiable
  * optionally enforce “all NOT NULL/no-default must be mapped” per critical table(s)
* **plugin logic** for:

  * lookup table matching
  * cross-tab relationships (units ↔ columns)
  * multi-table ordering
  * idempotent “get-or-create” behavior across multiple dependent inserts

### Dependency order (unchanged)

1. `refs` (independent)
2. `columns` (depends on refs; populates multiple tables)
3. `units` (depends on columns + lookups; populates multiple tables)

