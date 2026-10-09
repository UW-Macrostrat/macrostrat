"""Migrations for the usage-stats subsystem.

Registered by import, as `Migration.__subclasses__()` discovers them. Each gets
its own directory, since `Migration.apply` runs every `.sql` file beside it.
"""

from . import consolidation  # noqa: F401
