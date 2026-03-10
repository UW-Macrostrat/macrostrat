# Phase 3 Macrostrat Import Summary

## Purpose

Phase 3 is the first production-ready version of the Macrostrat Excel-to-database ingest pipeline. It is designed to import workbook data into Macrostrat in a way that is:

- idempotent on rerun
- robust to modest template evolution
- guarded against database schema drift
- auditable through external run artifacts
- modular enough to extend later without refactoring the core engine

Phase 3 ingests data from four Excel tabs:

- `metadata`
- `refs`
- `columns`
- `units`

It populates the following Macrostrat tables:

- `macrostrat.refs`
- `macrostrat.col_groups`
- `macrostrat.cols`
- `macrostrat.col_refs`
- `macrostrat.col_areas`
- `macrostrat.units`
- `macrostrat.unit_liths`
- `macrostrat.unit_liths_atts`
- `macrostrat.unit_environs`
- `macrostrat.unit_notes`
- `macrostrat.sections`
- `macrostrat.units_sections`

It does **not** insert strat-name-related database rows in Phase 3. Instead, it parses `strat_name` values and writes strat-name audit files for later use by a dedicated lexicon ingest workflow.

---

## High-level overview of script operation

At a high level, the script does the following:

1. Load the mapping JSON and confirm the Excel workbook is intended for that mapping version.
2. Read the workbook and normalize cell values by trimming whitespace.
3. Validate the `project_id` from Excel against both the Macrostrat API and the local database.
4. Introspect the database schema to verify that mapped fields exist and required unmapped columns are not missing for critical entities.
5. Begin a single database transaction.
6. Ingest references from the `refs` sheet.
7. Ingest column groups and columns from the `columns` sheet.
8. If unit rows are present, validate and normalize the `units` sheet, then ingest units and all unit-dependent relationships.
9. Recompute `sections` and `units_sections` when needed.
10. Commit the transaction on success.
11. Write audit artifacts to `./audit/` only after a successful commit.

The core design pattern is:

- **mapping-driven inserts** for stable entities and field lists
- **schema introspection guardrails** for compatibility and early failure
- **plugin-style logic** for identity rules, geometry handling, multi-table dependencies, and recomputed entities

---

## Files in Phase 3

### Primary code and configuration

- `macrostrat_import_3.0.py`
- `macrostrat_mapping_v3.0.json`

### Expected Excel workbook tabs

- `metadata`
- `refs`
- `columns`
- `units`

### Audit output directory

- `./audit/`

Audit files are written only after successful commit.

---

## Requirements and assumptions

## Environment assumptions

The script assumes:

- Python environment includes:
  - `requests`
  - `psycopg2`
  - `openpyxl`
- local PostgreSQL access to the target Macrostrat database
- PostGIS is available and functional for geometry validation and geometry inserts
- the Macrostrat API is reachable for project validation

## Workbook assumptions

The workbook must:

- include a `metadata` tab
- include `project_id` in `metadata`
- include `mapping_version` in `metadata`
- use `mapping_version = "3.0"`
- include tabs named exactly as expected in `macrostrat_mapping_v3.0.json`
- place headers in the first row of each tab

The `units` tab must exist, but it may contain zero data rows.

## Schema assumptions

The script assumes the target database schema is close enough to the mapped design that:

- mapped fields still exist
- critical required fields in `macrostrat.cols` and `macrostrat.units` remain satisfiable
- foreign key lookup tables contain the needed values for:
  - intervals
  - lithologies
  - lithology attributes
  - environments

## Operational assumptions

The pipeline is designed for rerunnable idempotent use.

That means:

- rerunning the same workbook should not create duplicate `refs`, `cols`, `units`, `unit_liths`, `unit_liths_atts`, `unit_environs`, or `unit_notes`
- `sections` and `units_sections` are treated as recomputable workbook-derived grouping tables
- on rerun, recompute of `sections` and `units_sections` is skipped when both:
  - `cols.inserted == 0`
  - `units.inserted == 0`

---

## Excel contract by tab

## `metadata`

Required keys:

- `project_id`
- `mapping_version`

Rules:

- `project_id` must be an integer
- `mapping_version` must exactly match the mapping JSON version

## `refs`

Required fields:

- `ref_id`
- `date`
- `title`
- `authors` or `author`

Rules:

- `ref_id` must be unique within the sheet
- `date` must be an integer year
- `title` must be non-empty
- at least one of `authors` or `author` must be non-empty

## `columns`

Required fields:

- `col_id`
- `col_name`
- `col_group`
- `ref_ids`
- `col_type`

Rules:

- `col_id` must be unique within the sheet
- `col_name` must be non-empty
- `col_group` must be non-empty
- `col_type` must be `column` or `section`
- `ref_ids` must resolve to `ref_id` values in the `refs` tab
- geometry can be provided as:
  - `lat` and `lng`
  - `geom`
  - or all three, provided `lat/lng` are consistent with the geometry
- `lat` and `lng` are stored consistently with `numeric(8,5)` in `macrostrat.cols`

## `units`

Required fields:

- `unit_id`
- `col_id`
- `section_id`
- `b_int`
- `t_int`
- `unit_name`
- `lithology`

Positional rule:

- either `position`
- or both `t_pos` and `b_pos`
# NB: a lot is placed on the user to make these informative; no validation between these and age assignments at this point

Additional optional fields include:

- `b_prop`
- `t_prop`
- `strat_name`
- `environment`
- `unit_description`
- `minor_lith`
- `min_thickness`
- `max_thickness`
- `comments`

---

## Detailed behavior by entity

## References

`refs` are ingested first.

Mapping highlights:

- `pub_year` ← Excel `date`
- `author` ← Excel `authors` or `author`
- `ref` ← concatenated citation text from title and publication
- `doi`, `url` nullable
- `compilation_code` defaults to empty string

Identity rule:

- `(pub_year, author, ref)`

Behavior:

- if existing reference found by natural key: reuse `refs.id`
- otherwise insert new reference and capture `refs.id`

Output:

- `ref_map[excel_ref_id] = refs.id`

## Column groups

`col_groups` are derived from distinct `col_group` values in the `columns` sheet.

Identity rule:

- `(project_id, col_group_long)`

Output:

- `col_groups_map[col_group] = col_groups.id`

## Columns

`cols` are ingested from the `columns` sheet with plugin-based identity and geometry handling.

Important points:

- point rows use `lat/lng` quantized to 5 decimal places to match `numeric(8,5)`
- polygon rows use `geom`
- rows with `geom` may also include `lat/lng`, but those must match the geometry-derived point-on-surface at 5 decimal places
- `coordinate` is populated as a PostGIS point
- `col_area` is set to `0.0` for lat/lng rows and computed geodesic area for polygon rows

Identity rule:

- shared keys:
  - `project_id`
  - `col_group_id`
  - `col_name`
  - `col_type`
  - `status_code`
- plus geometry branch:
  - polygon rows use `ST_Equals(poly_geom, ...)`
  - non-polygon rows use `lat`, `lng`, and `poly_geom IS NULL`

Dependent outputs:

- `col_refs`
- `col_areas` for polygon rows

Output:

- `col_map[excel_col_id] = cols.id`

## Units

`units` are ingested after columns.

Mappings:

- `col_id` ← resolved from Excel `col_id` via `col_map`
- `fo` ← resolved interval from Excel `b_int`
- `lo` ← resolved interval from Excel `t_int`
- `position_bottom` ← resolved `b_pos` or normalized `position`
- `position_top` ← resolved `t_pos` or normalized `position`
- `max_thick` ← Excel `max_thickness`
- `min_thick` ← Excel `min_thickness`
- `strat_name` ← Excel `unit_name`
- `fo_h` ← scaled `b_prop * 10000` or `NULL`
- `lo_h` ← scaled `t_prop * 10000` or `NULL`
- `date_mod = now()`
- `color = ''`
- `outcrop = ''`
- `section_id = 0` initially, then updated after section rebuild

Identity rule:

- `(col_id, strat_name, position_bottom, position_top, fo, lo)`

Behavior:

- existing rows are reused
- new rows are inserted
- `unit_map[excel_unit_id] = units.id`

## Unit lithologies

Parsed from:

- Excel `lithology` → dominant lithologies (`dom`)
- Excel `minor_lith` → subordinate lithologies (`sub`)

Syntax:

- `;` separates lithology entries
- within each entry, `,` separates tokens
- last token is lithology
- preceding tokens are lithology attributes

Example:

- `red, sandy, shale; limestone`

Identity rule for `unit_liths`:

- `(unit_id, lith_id, dom)`

Fields:

- `dom` and `prop` both set to `dom` or `sub`
- `comp_prop = 0`
- `mod_prop = 0`
- `toc = 0`
- `ref_id = 0`
- `date_mod = now()`

## Unit lithology attributes

Identity rule:

- `(unit_lith_id, lith_att_id)`

Fields:

- `ref_id = 0`
- `date_mod = now()`

## Unit environments

Parsed from Excel `environment`.

Syntax:

- `;` separates entries
- each entry may be an integer id or environment name

Identity rule:

- `(unit_id, environ_id)`

Fields:

- `ref_id = NULL`
- `date_mod = now()`

## Unit notes

Inserted only if either Excel `unit_description` or `comments` is non-empty.

Notes text logic:

- if only one is present, use that text
- if both are present, join with `'; '`

Identity rule:

- one note row per `unit_id`

Operational behavior:

- insert if no note exists
- reuse if note text matches
- update if existing note text differs

## Sections and units_sections

These are treated as recomputable grouping tables.

Excel section identity:

- `(excel col_id, excel section_id)`

Section bounds rule:

- `sections.fo` = oldest `b_int` among units in the section
- `sections.lo` = youngest `t_int` among units in the section

Operational behavior:

- for columns represented in the current workbook run, existing `units_sections` and `sections` rows are deleted and rebuilt
- rebuild is skipped when both:
  - no new columns were inserted
  - no new units were inserted

After rebuild:

- `units_sections` is repopulated
- `units.section_id` is updated to the rebuilt section id

---

## Validation and normalization rules

## General normalization

- all string cells are trimmed on read
- blank strings are treated as empty
- sheet header whitespace is trimmed

## Units-specific validation

- `unit_id` must be unique in the `units` sheet
- `col_id` must exist in the Excel `columns` sheet and resolve through `col_map`
- `section_id` must be integer
- `unit_name` must be non-empty
- `b_int` and `t_int` must resolve to `macrostrat.intervals`
- `intervals.age_bottom(b_int) >= intervals.age_bottom(t_int)`
- if both `b_pos` and `t_pos` are used, require `b_pos >= t_pos`
- if both `min_thickness` and `max_thickness` are present, require `max_thickness >= min_thickness`
- `b_prop` and `t_prop`, if present, must be between `0` and `1`
- if `b_int == t_int` and both proportions are present, require `b_prop < t_prop`
- strat-name hierarchy path depth must not exceed 8 names in the current preliminary audit implementation

## Duplicate normalized unit identity

Within a single workbook, duplicate normalized unit identities are treated as an error.

That identity is:

- `(db_col_id, unit_name, position_bottom, position_top, b_int_id, t_int_id)`

This prevents accidental duplicate unit rows from passing silently.

---

## Strat-name handling in Phase 3

Phase 3 does **not** insert any strat-name-related DB rows.

It does parse `strat_name` and writes preliminary audit files intended to support a later dedicated workflow for:

- `macrostrat.strat_names`
- `macrostrat.strat_tree`
- `macrostrat.unit_strat_names`

### Current strat_name syntax

- `;` separates multiple assigned name paths
- within a path, `,` separates ordered names
- first name = name applied to the unit
- following names = parent hierarchy upward

### Audit outputs

Two TSVs are written:

- `strat_name_lexicon_<project_id>_<runstamp>.tsv`
- `unit_strat_name_map_<project_id>_<runstamp>.tsv`

These capture:

- each unique normalized name+hierarchy path in the workbook
- each mapping from unit to normalized name path

---

## Audit outputs

After a successful commit, Phase 3 writes audit artifacts to `./audit/`.

Core files:

- `macrostrat_import_audit_<project_id>_<runstamp>.json`
- `ref_id_map_<project_id>_<runstamp>.tsv`
- `col_id_map_<project_id>_<runstamp>.tsv`
- `unit_id_map_<project_id>_<runstamp>.tsv`
- `strat_name_lexicon_<project_id>_<runstamp>.tsv`
- `unit_strat_name_map_<project_id>_<runstamp>.tsv`

The JSON manifest includes:

- run timestamp
- `project_id`
- `mapping_version`
- `script_name`
- `audit_dir`
- Excel filename
- `excel_sha256`
- output filenames
- per-entity processed/inserted/reused/updated/skipped counts

Audit artifacts are written only after successful commit, so they never describe a rolled-back transaction.

---

## Step-by-step operational flow

## Normal import

1. Prepare workbook with `mapping_version = 3.0` and valid `project_id`.
2. Confirm workbook contains `metadata`, `refs`, `columns`, and `units` tabs.
3. Run `macrostrat_import_3.0.py` with `macrostrat_mapping_v3.0.json`.
4. Review console summaries for inserts, reuse, and any skipped rebuild steps.
5. Review audit files in `./audit/`.

## Pure rerun of same workbook

Expected behavior:

- no new refs inserted
- no new columns inserted
- no new units inserted
- dependent unit joins reused
- section rebuild skipped
- fresh audit files still written for the rerun

## Workbook with empty units tab

Expected behavior:

- refs and columns ingest normally
- units ingest is skipped cleanly
- `unit_id_map` is header-only
- strat-name audit files are header-only
- audit manifest records units as skipped

---

## Requirements and assumptions for future revisions

The pipeline is intentionally designed so that moderate changes to the Excel template or database schema can be incorporated systematically. The correct procedure is to treat any such revision as a controlled update, not as an ad hoc code tweak.

---

## What to do when the Excel template changes

If the workbook template changes, follow these steps in order.

### 1. Identify the exact nature of the change

Determine whether the change is:

- a header rename only
- an added optional field
- an added required field
- a removed field
- a field that changes meaning or syntax
- a new sheet
- a reorganization that affects identity or relationships

### 2. Decide whether the change is backward-compatible within Phase 3

If the change is small and does not alter semantics, you may be able to:

- update mapping JSON only
- update parser aliases or expected headers
- keep `mapping_version = 3.0`

If the change affects semantics, identity, or validation rules, treat it as a new mapping version.

### 3. Update the Excel contract in code-facing terms

Before editing code, write down:

- exact new header names
- required vs optional status
- allowed value syntax
- validation rules
- whether existing identity rules remain correct

### 4. Update `macrostrat_mapping_v3.0.json` or create a new mapping version

Update the mapping file if the change affects:

- sheet names
- mapped entities
- mapped fields
- handler requirements

Bump `mapping_version` if the change alters the workbook contract materially.

### 5. Update parser and validation logic

If the changed field is plugin-handled, update:

- units parser helpers
- columns parser helpers
- field-specific validation rules
- any normalization logic

### 6. Update audit outputs if needed

If the new Excel field affects:

- unit identity
n- audit usefulness
- strat-name interpretation

then update the relevant TSV or manifest outputs.

### 7. Test three cases

Always test:

1. first import
2. pure rerun
3. workbook with empty units tab

If the change affects columns or geometry, also test:

- lat/lng-only rows
- geom-only rows
- lat/lng + geom rows

### 8. Only then use revised workbooks operationally

Do not mix a revised workbook template into normal use until:

- mapping/version logic is updated
- validation passes cleanly
- rerun behavior is confirmed

---

## What to do when the database schema changes

If the target Macrostrat schema changes, follow these steps in order.

### 1. Identify the exact schema change

Determine whether the change is:

- new nullable column
- new NOT NULL column with default
- new NOT NULL column without default
- renamed column
- removed column
- changed type/precision
- changed lookup table field names
- changed foreign key expectations

### 2. Run the script and inspect the failure mode

Phase 3 intentionally fails early for many schema-drift cases through:

- mapped-column existence checks
- required-column satisfiability checks
- explicit NOT NULL coverage checks for `macrostrat.cols` and `macrostrat.units`

Use the failure output to identify whether the issue is:

- mapping-only
- plugin-only
- validation-only
- true incompatible schema change

### 3. Update mapping JSON for mapped-field changes

If a mapped DB column changed name or status, update:

- target table field names
- `omit_if_none` usage
- constants/defaults/handlers

### 4. Update handlers and parser logic for type or semantic changes

Examples:

- coordinate precision changes
- nullable vs non-nullable changes
- `ref_id = NULL` vs `0`
- new lookup table field names

### 5. If a new NOT NULL/no-default column is added to a critical table

Do **not** bypass the guardrail.

Instead:

1. identify the intended source of the value
2. decide whether it belongs in mapping JSON or plugin logic
3. implement the value generation explicitly
4. rerun schema validation

This is especially important for:

- `macrostrat.cols`
- `macrostrat.units`

### 6. Reevaluate identity rules when relevant

If schema changes affect the meaning of uniqueness, ask explicitly whether the current natural keys remain valid.

Important entities to re-check:

- `refs`
- `cols`
- `units`
- `unit_liths`
- `unit_environs`

### 7. Re-test first import and rerun behavior

Any schema change affecting inserts or keys must be followed by:

- first-run test
- pure rerun test
- affected edge-case test

### 8. Document the change in the mapping version or release notes

If the schema change required meaningful code or contract changes, update:

- mapping version if appropriate
- internal documentation
- any workbook template instructions

---

## Safe revision checklist

Use this checklist whenever either the Excel template or database schema changes.

1. Describe the change precisely.
2. Decide whether it changes the workbook contract.
3. Decide whether `mapping_version` should change.
4. Update mapping JSON if needed.
5. Update parser/validation/handlers if needed.
6. Re-run schema guardrails.
7. Test first import.
8. Test pure rerun.
9. Test empty units tab.
10. Review audit outputs.
11. Only then release the revised workflow for operational use.

---

## Current Phase 3 status

Phase 3 is now a solid operational pipeline with:

- strong validation
- schema-aware safety checks
- rerunnable idempotent behavior for core entities
- recomputed grouping logic where appropriate
- workbook-attached provenance through external audit artifacts
- a clear boundary between unit ingest and future strat-name lexicon ingest

The next major independent development path is the dedicated strat-name ingest workflow.

