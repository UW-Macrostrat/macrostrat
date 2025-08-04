from starlette.config import Config
from os import path

config = Config(".env")

DATABASE = config("GEOLOGIC_MAP_DATABASE")
IMPORTER_API = config("IMPORTER_API")
EXPORTER_API = config("EXPORTER_API")
