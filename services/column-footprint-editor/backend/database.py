from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

#from settings import DATABASE
from utils import run_sql_file, run_sql, run_query


here = Path(__file__).parent
fixtures = here / "fixtures"

class Database:

    engine = create_engine("postgresql://postgres@localhost:54321/geologic_map", echo=True)
    Session = sessionmaker(bind=engine)

    @classmethod
    def run_sql_file(cls, sql_file, params):
        return run_sql_file(sql_file, params=params, session=cls.Session())

    @classmethod
    def exec_query(cls, *args):
        """
            Returns a Pandas DataFrame from a SQL query
            need to pass query as sql
        """
        return run_query(cls.engine, *args)

    @classmethod
    def print_hello(cls):
        '''Class method to test if I have imported database class'''
        print("Hello")