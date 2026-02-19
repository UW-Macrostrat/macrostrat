from warnings import filterwarnings

import psycopg2
import pymysql
from pymysql.cursors import SSDictCursor
from sqlalchemy import create_engine

from macrostrat.core.config import MYSQL_DATABASE, PG_DATABASE
from macrostrat.core.database import get_database, refresh_database


# Connect to MySQL
def mariaConnection():
    _url = MYSQL_DATABASE.replace("mysql://", "mysql+pymysql://")
    url = create_engine(_url).url

    # Ignore warnings from MariaDB
    filterwarnings("ignore", category=pymysql.Warning)
    return pymysql.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        passwd=url.password,
        db=url.database,
        cursorclass=SSDictCursor,
        read_timeout=180,
    )


# Connect to Postgres
def pgConnection():
    pg_conn = psycopg2.connect(PG_DATABASE)
    pg_conn.set_client_encoding("utf8")
    return pg_conn


def get_pg_credentials():
    db = get_database()
    return db.engine.url


def get_db():
    return get_database()


def refresh_db():
    return refresh_database()
