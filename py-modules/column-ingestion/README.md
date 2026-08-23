# Column ingestion

Macrostrat utilities for stratigraphic column ingestion.

## Entry points

`ingest_columns_from_file(db, path)` reads an ingestion workbook. It is a front-end
to **`ingest_columns(db, columns, project=...)`**, which takes `Column` objects with
their `units` already populated — the seam for data that never was a spreadsheet.
Both run the whole `(column, sections, units, age model)` set in one transaction.

## Age provenance

`BoundaryStatus` records where a boundary's age came from, and every value except
`ABSOLUTE` is stored the same way: an interval plus a proportion through it.
`RelativeAge.from_absolute(db, age)` converts a known number into that form, which
is what a dataset whose ages are plain numbers needs in order to be storable at all.

A caller that states a status keeps it. `MODELED` is the placeholder meaning "not
yet known whether this surface is constrained", and it is the only status the model
overwrites — so a dataset setting `Unit.age_status = BoundaryStatus.IMPOSED` on its
units gets `imposed` boundaries rather than being silently relabelled `relative`.
