"""Re-export: notices now live in `macrostrat.column_utils.notices`.

Kept as a shim so the many `from . import notices` / `from .. import notices`
call sites in this package are unchanged. The functions operate on the collector
context variables defined in `column_utils.notices`, so a collector opened through
this module is the one `LithsProcessor` (now in column-utils) reports into.
"""

from macrostrat.column_utils.notices import (  # noqa: F401
    LOCATION_FIELDS,
    IngestValidationError,
    Level,
    Notice,
    Notices,
    collect_notices,
    current_notices,
    error,
    error_or_raise,
    info,
    notice_context,
    report,
    warning,
)
