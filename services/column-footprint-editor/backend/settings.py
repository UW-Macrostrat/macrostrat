from starlette.config import Config
from os import path

config = Config(".env")

DATABASE = config("DATABASE")