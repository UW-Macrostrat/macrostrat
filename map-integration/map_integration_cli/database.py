from os import environ
from macrostrat.database import Database
from dotenv import load_dotenv

load_dotenv()

MACROSTRAT_DATABASE_URL = environ.get("MACROSTRAT_DATABASE_URL", None)

db = Database(MACROSTRAT_DATABASE_URL)
