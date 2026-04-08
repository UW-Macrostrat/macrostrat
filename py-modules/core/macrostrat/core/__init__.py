from .main import Macrostrat

app = Macrostrat()

# This has to happen after the macrostrat config
from .database import get_database  # noqa
