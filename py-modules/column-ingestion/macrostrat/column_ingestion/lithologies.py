"""Re-export: the lithology matcher now lives in
`macrostrat.column_utils.lithologies`, so the API can run it without the importer's
dependency stack. Kept as a shim for existing imports in this package."""

from macrostrat.column_utils.lithologies import (  # noqa: F401
    LithAbundance,
    LithAtt,
    Lithology,
    LithsProcessor,
    MultipleLithologiesError,
    split_domains,
    split_words,
)
