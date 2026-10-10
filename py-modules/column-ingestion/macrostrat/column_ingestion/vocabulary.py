"""The controlled vocabularies one ingest resolves against, loaded once."""

from __future__ import annotations

from .environs import EnvironsProcessor
from .lithologies import LithsProcessor


class Vocabulary:
    """Lithology and environment processors.

    Each processor fetches its lookup table on construction, so building them per
    section — as the parser used to — cost a round trip per section. One instance is
    made per run and handed down.
    """

    def __init__(self, db):
        self.liths = LithsProcessor(db)
        self.environs = EnvironsProcessor(db)
        #: The run's `facies` sheet, by `facies_id` (see `facies.facies_from_df`).
        self.facies: dict = {}
