import urllib.parse

import pytest
from api.query_parser import QueryParser
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.sql.expression import SQLColumnExpression
from starlette.datastructures import Headers
from starlette.requests import QueryParams


def compile_statement(stmt: SQLColumnExpression):
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


TEST_TABLE = Table(
    "test_table",
    MetaData(),
    Column("string_column", String),
    Column("int_column", Integer),
)


class TestParser:

    def test_eq(self):
        params = {"string_column": "eq.test value"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.string_column = 'test value'"

    def test_eq_int(self):
        """For this test there is no point to cast as postgres will do that on its side automatically"""

        params = {"int_column": "eq.1"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.int_column = 1"

    def test_encoded_spaces_in_value(self):
        params = {"string_column": "eq.test%20value"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.string_column = 'test value'"

    def test_multiple_eq(self):
        params = {"int_column": "eq.1", "string_column": "eq.test value"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert (
            compile_statement(sql)
            == "test_table.int_column = 1 AND test_table.string_column = 'test value'"
        )

    def test_like(self):
        params = {"string_column": "like.%its rock time%"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert (
            compile_statement(sql) == "test_table.string_column LIKE '%its rock time%'"
        )

    def test_encoded_like(self):
        params = {"string_column": "like.%its%20rock%20time%"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert (
            compile_statement(sql) == "test_table.string_column LIKE '%its rock time%'"
        )

    def test_is_null(self):
        params = {"int_column": "is.null"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.int_column IS NULL"

    def test_is_true(self):
        params = {"int_column": "is.true"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.int_column IS true"

    def test_is_false(self):
        params = {"int_column": "is.false"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.int_column IS false"

    def test_is_not_null(self):
        params = {"string_column": "not.is.null"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.string_column IS NOT NULL"

    def test_is_not_like(self):
        params = {"string_column": "not.like.%value%"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.string_column NOT LIKE '%value%'"

    def test_period_in_string(self):
        params = {"string_column": "like.%2.5 Ga to 3.2 Ga%"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert (
            compile_statement(sql)
            == "test_table.string_column LIKE '%2.5 Ga to 3.2 Ga%'"
        )

    def test_period_in_string(self):
        params = {"string_column": "like.Felsic"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        sql = query_parser.where_expressions()

        assert compile_statement(sql) == "test_table.string_column LIKE '%Felsic%'"

    def test_group_by(self):
        params = {"int_column": "group_by"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )

        assert query_parser.get_group_by_column().name == "int_column"

        select_columns = query_parser.get_select_columns()

        stmt = [*map(lambda x: compile_statement(x), select_columns)]

        assert (
            stmt[0]
            == "CASE WHEN (count(DISTINCT CAST(test_table.string_column AS VARCHAR)) > 5) THEN 'Multiple Values' ELSE STRING_AGG(DISTINCT CAST(test_table.string_column AS VARCHAR), ',') END"
        )
        assert stmt[1] == "test_table.int_column"

    def test_order_by(self):
        params = {"int_column": "order_by"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        assert query_parser.get_order_by_columns()[0].name == "int_column"

    def test_order_by_multiple(self):
        params = {"int_column": "order_by", "string_column": "order_by"}

        query_parser = QueryParser(
            columns=TEST_TABLE.columns, query_params=params.items()
        )
        assert query_parser.get_order_by_columns()[0].name == "int_column"
        assert query_parser.get_order_by_columns()[1].name == "string_column"
