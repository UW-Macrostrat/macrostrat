# Loading working data

`macrostrat db load-csv` and `macrostrat db load-geo` pull tabular and geospatial
files into the database, **creating the destination table to match the file**.
They behave like PostgreSQL's `COPY`, except you don't have to write the
`CREATE TABLE` first.

These are tools for *working data*: a spreadsheet a collaborator sent, a
shapefile you want to look at in QGIS, an extract you need to join against
Macrostrat tables. They are deliberately not part of the map-ingestion pipeline —
for source maps with slugs, provenance and review state, use
`macrostrat maps ingest` instead.

By default, tables are named after their file and land in the `temp` schema:

```bash
macrostrat db load-csv "Sample Ages.csv"        # -> temp.sample_ages
macrostrat db load-geo units.gpkg               # -> temp.units_<layer>, one per layer
```

Nothing cleans `temp` up for you. Treat it as a scratch space, and drop what you
are done with.

## Shared behaviour

Both commands work the same way, and share their implementation, so these rules
hold for either one.

**Table naming.** The table is named after the file, with every suffix stripped
and the name sanitized (`Sample Ages.csv` → `sample_ages`, `big.csv.gz` → `big`).
Override with `--table`/`-t`, which is only valid when loading a single
file/layer. Use `--schema`/`-n` to write somewhere other than `temp`, and
`--database` to target a database other than the configured default.

**Column naming.** Headers are sanitized into unquoted-safe identifiers:
camel-case is split, punctuation collapses to underscores, everything is
lowercased, and names are truncated to Postgres' 63-byte limit. Duplicates get a
counter suffix. Wherever a name had to be changed, the original is preserved as
a column comment, so nothing is lost:

| Source header | Column       | Comment      |
| ------------- | ------------ | ------------ |
| `Sample ID`   | `sample_id`  | `Sample ID`  |
| `age (Ma)`    | `age_ma`     | `age (Ma)`   |
| `IsPrimary`   | `is_primary` | `IsPrimary`  |
| `age (Ma)` #2 | `age_ma_2`   | `age (Ma)`   |

**Existing tables.** By default, loading into a table that already exists is an
error. `--replace` drops and recreates it; `--append` adds to it as-is. The two
are mutually exclusive.

**Previewing.** `--dry-run` prints the `CREATE TABLE` that *would* be run and
touches nothing. Use it to check inferred types before committing to a load.

```bash
macrostrat db load-csv measurements.csv --dry-run
macrostrat db load-geo units.gpkg --layer map_units --dry-run
```

**Inspecting the result.** `macrostrat db tables --schema temp` lists what you
have loaded; `macrostrat db inspect temp.sample_ages` opens a shell on one table.

## Loading CSVs

```bash
macrostrat db load-csv data.csv
macrostrat db load-csv exports/*.csv --replace
macrostrat db load-csv data.tsv --separator $'\t'
cat data.csv | macrostrat db load-csv - --table my_data
```

Compressed files (`.csv.gz`) are read directly.

**Type inference** scans the **whole file** by default. This is slower than
sampling, but a partial scan silently mistypes any column whose surprises come
late — a text column that looks numeric for the first thousand rows, an integer
column that turns out to hold decimals. Restrict it with `--infer-rows N` if you
have a very large file and know the first N rows are representative.

Empty fields become `NULL`. If the file spells missing values some other way,
declare them with `--null` (repeatable):

```bash
macrostrat db load-csv survey.csv --null NA --null -999 --null "n/a"
```

`--all-text` skips inference entirely and makes every column `text`. Reach for it
when a file is messy enough that you would rather clean it in SQL, or when
inference guesses a type you don't want.

### CSV files from spreadsheets

Files exported from Excel — Mac versions especially — routinely arrive with a
UTF-8 BOM, `\r`-only line endings, and stray zero-width spaces inside values.
Polars tolerates the first two, so a load can *succeed* while leaving invisible
characters in your data. If values won't match anything you join them against,
check for this:

```bash
# CR-only line endings (file looks like a single line to most tools)
tr -cd '\r' < suspect.csv | wc -c
# BOM: efbbbf means the first header name has one glued on
head -c 3 suspect.csv | xxd -p
# non-ASCII survey, including invisible characters
python3 -c "import collections,sys;print(collections.Counter(c for c in open(sys.argv[1],encoding='utf-8').read() if ord(c)>126).most_common())" suspect.csv
```

A ragged row count is the other common problem: a load fails outright if any row
has more fields than the header, which usually means an unlabelled extra column
rather than genuine corruption.

## Loading geospatial data

```bash
macrostrat db load-geo units.gpkg                        # every layer, one table each
macrostrat db load-geo maps/*.shp --replace
macrostrat db load-geo units.gpkg --layer map_units --table units
macrostrat db load-geo units.gpkg --where "confidence >= 2"
```

Reading is done with [pyogrio](https://pyogrio.readthedocs.io/), a direct
GDAL/OGR binding, so anything `ogr2ogr` can read works here: Shapefile,
GeoPackage, GeoJSON, FileGDB, KML and the rest. Nothing is shelled out to, and
database credentials never appear on a command line.

`--where` is an OGR attribute filter applied while reading, so it is evaluated
by the driver rather than after loading. It refers to **source** column names,
before sanitization.

**Layers become tables.** A multi-layer file loads every layer, each into its
own table named `<file>_<layer>`. A single-layer file, or one whose layer shares
its name, is named after the file alone. `--layer`/`-l` picks one layer.

**Coordinate reference systems.** Geometries are reprojected to **EPSG:4326** by
default, matching the rest of Macrostrat.

```bash
macrostrat db load-geo units.gpkg --srid 3857     # reproject somewhere else
macrostrat db load-geo units.gpkg --keep-srid     # don't reproject at all
macrostrat db load-geo nocrs.shp --source-srid 26915
```

- `--srid` sets the target to reproject *to*.
- `--keep-srid` keeps the file's own CRS, declaring the geometry column with that
  SRID. Mutually exclusive with `--srid`.
- `--source-srid` declares what the file *is*, for a file carrying no CRS or a
  wrong one. It does not by itself prevent reprojection — the target still
  applies — so the three compose as you would expect:

  ```bash
  # declare 26915, then normalize to 4326
  macrostrat db load-geo nocrs.shp --source-srid 26915
  # declare 26915 and stay there
  macrostrat db load-geo nocrs.shp --source-srid 26915 --keep-srid
  # declare 26915, reproject to web mercator
  macrostrat db load-geo nocrs.shp --source-srid 26915 --srid 3857
  ```

A file with no CRS is assumed to be in the target SRID, with a warning. Because
a PostGIS SRID has to be a number, `--keep-srid` fails on a file whose CRS has
no EPSG code (a custom projection, say) — reproject it, or supply the equivalent
code with `--source-srid`.

**Geometry column.** Called `geom` by default, per Macrostrat convention;
`--geometry-column`/`-g` renames it. A GIST index is created on it unless you
pass `--no-index`.

**Geometry typing.** The column is declared with the narrowest PostGIS type that
covers the layer — `geometry(Polygon, 4326)` for a polygon layer. A layer with
mixed geometry types falls back to `geometry(Geometry, srid)`, and a `Z`
dimension present on every feature is preserved (`PointZ`). `--multi` promotes
single geometries to their `Multi*` equivalents, which is the usual fix for a
layer that is *almost* uniform:

```bash
macrostrat db load-geo units.gpkg --multi     # Polygon + MultiPolygon -> MultiPolygon
```

Null geometries are loaded as `NULL` rather than being dropped.

## Notes for maintainers

The commands live in `py-modules/cli/macrostrat/cli/database/`:
`load_csv.py`, `load_geo.py`, and `load_utils.py` for everything they share —
identifier sanitization, type mapping, table creation, and the `COPY` itself.
Changes to shared behaviour belong in `load_utils.py` so the two cannot drift.

A few decisions worth knowing before changing this code:

- **Data always moves via `COPY … FROM STDIN`**, in 10k-row batches, driven
  through the raw DBAPI connection. A raw psycopg cursor used inside a SQLAlchemy
  `Connection` is invisible to that connection's transaction bookkeeping, so the
  `COPY` gets rolled back when the `Connection` closes — hence
  `engine.raw_connection()` and an explicit `commit()`.
- **Attribute types are inferred by Polars** for both commands. `load-geo` reads
  through geopandas and converts, because `pl.from_pandas` needs pyarrow for
  anything that is not a plain numpy column — a heavy dependency for a handoff.
  The converter in `load_utils.polars_from_pandas` also normalizes two
  pandas-isms: extension dtypes carry `pd.NA` (which Polars rejects), and missing
  numbers arrive as `NaN`, which Postgres would otherwise store as a literal
  `NaN` instead of `NULL`.
- **Geometry travels as hex WKB** in the same `COPY` stream; PostGIS parses it on
  input. Hex WKB carries no SRID, so the geometry column is created untyped and
  then constrained with a single
  `ALTER … TYPE geometry(<type>, <srid>) USING ST_SetSRID(...)` after the copy.
- **Dynamic SQL is composed with `psycopg.sql`** (`Identifier`, `Literal`) passed
  as parameters to `run_sql`. Note that `run_sql`/`run_query` accept a composed
  statement only as a *parameter value*, not as the query itself, and that
  `COMMENT ON … IS` cannot take a bind parameter — its text has to be inlined as
  a `Literal`.

`--append` skips the post-copy steps, since the column is already typed and
indexed. That means appending geometries in a different SRID from the existing
column is rejected by Postgres rather than silently reprojected.

### Possible future direction

The machinery in `load_utils.py` — identifier sanitization, Polars-to-PostgreSQL
type mapping, table creation and the `COPY` itself — is generic, and not really
specific to Macrostrat. Once these commands have been validated in practice, it
is worth **migrating them to a shared library**, most naturally
`macrostrat.database` in the `python-libraries` repo, leaving thin CLI wrappers
here. Keeping shared behaviour consolidated in `load_utils.py` rather than
duplicated across the two commands is what keeps that extraction cheap; please
preserve that split.

Also unresolved: `load-geo` reads through geopandas only because reprojection
needs pyproj. `pyogrio.raw.read` is a pandas-free path that returns numpy arrays
and WKB directly, and reprojection could move into PostGIS by folding
`ST_Transform` into the post-copy `ALTER`. The obstacle is that a custom
(non-EPSG) CRS has no SRID to transform *from*, so a geopandas fallback would
still be needed for those files.
