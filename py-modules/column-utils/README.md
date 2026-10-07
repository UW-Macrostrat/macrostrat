# macrostrat.column-utils

Utilities for Macrostrat columns that more than one service needs: the column importer
(`macrostrat.column-ingestion`) and the v3 API both depend on it. Dependencies stay
light — SQLAlchemy and PostGIS through GeoAlchemy2 — so the API can import it without
the importer's spreadsheet stack.

- `geometry` — a column's point and polygon resolved into what `macrostrat.cols` holds,
  and written to `cols` and `col_areas`.
