from .base import Base
import sys
import datetime
from psycopg2.extensions import AsIs
from .table_meta import *
import urllib.request, urllib.error, urllib.parse


class Schlep(Base):
    """
    macrostrat schlep <table>:
        Move a table from MariaDB to Postgres

    Available tables:
        autocomplete
        col_areas
        refs
        cols
        intervals
        timescales
        liths
        strat_names_meta
        col_refs
        concepts_places
        units
        lookup_strat_names
        unit_strat_names
        units_sections
        strat_names
        strat_tree
        unit_liths
        strat_names_places
        col_groups
        places
        projects
        lookup_unit_intervals
        lith_atts
        lookup_unit_liths
        timescales_intervals
        measures
        measuremeta
        measurements

        all - will move all above tables

    Usage:
      macrostrat schlep <table>
      macrostrat schlep all
      macrostrat schlep -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat schlep strat_names
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    def move_table(self, table):
        if table not in tables:
            print("Table not found")

        print("     %s" % (table,))
        # Clean up
        self.pg["cursor"].execute(
            "DROP TABLE IF EXISTS macrostrat.%(table)s_new", {"table": AsIs(table)}
        )
        self.pg["connection"].commit()

        # Create the new table in Postgres
        self.pg["cursor"].execute(tables[table]["create"])
        self.pg["connection"].commit()

        # Dump the data from MariaDB
        self.mariadb["cursor"].execute(tables[table]["dump"])

        # Iterate on each row and insert into Postgres
        row = self.mariadb["cursor"].fetchone()
        while row is not None:
            self.pg["cursor"].execute(tables[table]["insert"], row)
            row = self.mariadb["cursor"].fetchone()
        self.pg["connection"].commit()

        # Add any indexes
        if "index" in tables[table] and len(tables[table]["index"].strip()) > 0:
            self.pg["cursor"].execute(tables[table]["index"])
            self.pg["connection"].commit()

        # Run processing steps, if needed
        if len(tables[table]["process"].strip()) != 0:
            self.pg["cursor"].execute(tables[table]["process"])
            self.pg["connection"].commit()

        # Rename the table, drop the old one, add updated comment
        self.pg["cursor"].execute(
            """
            COMMENT ON TABLE macrostrat.%(table)s_new IS %(time)s;
            ALTER TABLE IF EXISTS macrostrat.%(table)s RENAME TO %(table)s_old;
            ALTER TABLE macrostrat.%(table)s_new RENAME TO %(table)s;
            DROP TABLE IF EXISTS macrostrat.%(table)s_old CASCADE;
        """,
            {
                "table": AsIs(table),
                "time": "Last updated from MariaDB - "
                + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
        self.pg["connection"].commit()

    def run(self):
        # Check if a command was provided
        if len(self.args) == 1:
            print("Please specify a table to move from MariaDB to Postgres")
            for table in tables:
                print("   %s" % (table,))
            sys.exit()

        # Validate the passed table
        table = self.args[1]
        if table not in tables and table != "all":
            print("Invalid table")
            sys.exit()

        if table == "all":
            for t in tables:
                Schlep.move_table(self, t)
        else:
            Schlep.move_table(self, table)

        try:
            urllib.request.urlopen(
                "http://127.0.0.1:5000/api/v2/columns/refresh-cache?cacheRefreshKey=%s"
                % (self.credentials["cacheRefreshKey"],)
            ).read()
        except:
            print("API cache was not updated")
