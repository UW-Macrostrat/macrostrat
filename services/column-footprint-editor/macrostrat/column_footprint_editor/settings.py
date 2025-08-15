from starlette.config import Config

config = Config(".env")

DATABASE = config("GEOLOGIC_MAP_DATABASE")
IMPORTER_API = config("IMPORTER_API")
EXPORTER_API = config("EXPORTER_API")
