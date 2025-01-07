import os

# Set the PG_DATABASE environment variable to a shim value, since
# tests cannot run without a database connection string defined.
# The strategy for dealing with this will have to be improved in the future.

if "PG_DATABASE" not in os.environ:
    os.environ["PG_DATABASE"] = (
        "postgresql://nonexistent-host.local:54328/nonexistent-database"
    )
