"""Shared lookups over Macrostrat's lithology vocabulary.

Moved here from `column-ingestion` so the API can run the same lithology matcher
without pulling the importer's heavy dependency stack.
"""


def get_all_liths(db):
    """Every lithology as `(id, name)` rows (`name` aliased from `lith`)."""
    return db.run_query("SELECT id, lith name FROM macrostrat.liths").fetchall()


def get_all_lith_attributes(db):
    """Every lithology attribute as `(id, name)` rows (`name` from `lith_att`)."""
    return db.run_query(
        "SELECT id, lith_att name FROM macrostrat.lith_atts"
    ).fetchall()
