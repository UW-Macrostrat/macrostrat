import os
from dotenv import load_dotenv

load_dotenv()

MARIADB_CONFIG = {
    "host": os.getenv("MARIADB_HOST"),
    "user": os.getenv("MARIADB_USER"),
    "password": os.getenv("MARIADB_PASSWORD"),
    "database": os.getenv("MARIADB_DATABASE")
}
