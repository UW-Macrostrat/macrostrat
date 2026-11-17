# macrostrat.loader_utils

Load working data into PostgreSQL: a table is created to match the file and the
rows are streamed in with `COPY`. This is the library behind `macrostrat db
load-csv` and `macrostrat db load-geo`, and what data-integration pipelines call
to bring GIS layers into `temp`.

Functions take a SQLAlchemy `Engine` and raise `LoadError` when a load cannot
proceed as asked, so they work the same from the CLI, a pipeline or a notebook.

```python
from macrostrat.loader_utils import load_layer

load_layer(
    db.engine,
    "units.gpkg",
    "polygons",
    table="units_raw",  # in `temp` by default
    fid_column="objectid",  # keep the GeoPackage feature ID
    promote_to_multi=True,
    replace=True,
)
```

Layers are reprojected to EPSG:4326 unless told otherwise. Column names are
lowercased and made safe as identifiers (`MapNumber` → `map_number`), with the
original name recorded as a column comment.

See `docs/Loading working data.md` for the behaviour shared with the CLI.
