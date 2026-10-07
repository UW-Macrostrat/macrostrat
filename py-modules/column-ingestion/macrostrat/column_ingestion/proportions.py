"""Re-export: the proportion syntax now lives in
`macrostrat.column_utils.proportions`. Kept as a shim for existing imports."""

from macrostrat.column_utils.proportions import (  # noqa: F401
    ABUNDANCE_TERMS,
    Proportion,
    parse_proportion,
    share_remaining,
    split_proportion,
)
