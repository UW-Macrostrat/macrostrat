from abc import abstractmethod
import pymysql
import pymysql.cursors
from warnings import filterwarnings
import psycopg2
from psycopg2.extras import NamedTupleCursor
import yaml
import os

class Base(object):

    def __init__(self, connections, *args):
        # Load the credentials file
        with open(os.path.join(os.path.dirname(__file__), '../../credentials.yml'), 'r') as f:
            self.credentials = yaml.load(f)

        # Connect to MySQL
        def mariaConnection():
            # Ignore warnings from MariaDB
            filterwarnings('ignore', category = pymysql.Warning)
            return pymysql.connect(host=self.credentials['mysql_host'], user=self.credentials['mysql_user'], passwd=self.credentials['mysql_passwd'], db=self.credentials['mysql_db'], unix_socket=self.credentials['mysql_socket'], cursorclass=pymysql.cursors.SSDictCursor, read_timeout=180)

        # Connect to Postgres
        def pgConnection():
            pg_conn = psycopg2.connect(dbname=self.credentials['pg_db'], user=self.credentials['pg_user'], host=self.credentials['pg_host'], port=self.credentials['pg_port'])
            pg_conn.set_client_encoding('Latin1')
            return pg_conn

        self.mariadb = {
            'connection': mariaConnection(),
            'cursor': None,
            'raw_connection': mariaConnection
        }
        self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.pg = {
            'connection': pgConnection(),
            'cursor': None,
            'raw_connection': pgConnection
        }
        self.pg['cursor'] = self.pg['connection'].cursor(cursor_factory = NamedTupleCursor)

        self.args = args

    @abstractmethod
    def run(self):
        return None
