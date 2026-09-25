"""Re-apply the re-runnable content of a set of schema chunks.

What `macrostrat schema sync` does, for any caller holding a database and the
chunks: the command itself, and a migration that names the chunks whose code
objects its change touches (`Migration.sync_chunks`).
"""

from dataclasses import dataclass, field
from typing import Optional

from macrostrat.database import Database

from .rebuild import RebuildReport
from .views import ViewRebuildReport


@dataclass
class SyncReport:
    procedures: Optional[RebuildReport] = None
    views: Optional[ViewRebuildReport] = None
    data: Optional[RebuildReport] = None
    permissions: Optional[RebuildReport] = None
    failures: list[str] = field(default_factory=list)


def sync_schema_chunks(
    db: Database,
    chunks,
    *,
    views: bool = True,
    procedures: bool = True,
    data: bool = True,
    permissions: bool = True,
) -> SyncReport:
    """Re-apply the views, procedures, seed data and permissions of `chunks`.

    Dependencies first (functions before the views and seed rows that use them);
    permissions last -- roles and grants are swept together, in the order the
    schema declares them, so each grant follows the role it names.
    """
    from .grants import rebuild_grants
    from .procedures import rebuild_procedures
    from .seed_data import rebuild_seed_data
    from .views import rebuild_views

    report = SyncReport()
    if procedures:
        report.procedures = rebuild_procedures(db, chunks)
        report.failures += report.procedures.failed
    if views:
        report.views = rebuild_views(db, chunks)
    if data:
        report.data = rebuild_seed_data(db, chunks)
        report.failures += report.data.failed
    if permissions:
        report.permissions = rebuild_grants(db, chunks)
        report.failures += report.permissions.failed

    db.run_sql("NOTIFY pgrst, 'reload schema';")
    return report
