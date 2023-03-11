from abc import abstractmethod
from psycopg2.extras import NamedTupleCursor
from ..database import mariaConnection, pgConnection


class Base(object):
    def __init__(self, connections, *args):
        self.mariadb = {
            "connection": mariaConnection(),
            "cursor": None,
            "raw_connection": mariaConnection,
        }
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.pg = {
            "connection": pgConnection(),
            "cursor": None,
            "raw_connection": pgConnection,
        }
        self.pg["cursor"] = self.pg["connection"].cursor(
            cursor_factory=NamedTupleCursor
        )

        self.credentials = None

        self.args = args

    @abstractmethod
    def run(self):
        return None
