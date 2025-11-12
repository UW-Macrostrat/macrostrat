from pathlib import Path

__dir__ = Path(__file__).parent


# TODO: break this into smaller atomic migrations
from macrostrat.core.migrations import Migration, ReadinessState


class MacrostratLexiconViewsMigration(Migration):
    name = "lexicon-views"
    description = """Create views for lexicon PostgREST APIs"""
    readiness_state = ReadinessState.ALPHA
    depends_on = ["api-v3"]
    always_apply = True
