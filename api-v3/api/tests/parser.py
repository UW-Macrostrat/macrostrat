import pytest

import urllib.parse

from sqlalchemy import Table, MetaData, Column, String

from api.query_parser import query_parser

from starlette.requests import QueryParams
from starlette.datastructures import Headers

from sqlalchemy.sql.expression import SQLColumnExpression


def compile_statement(stmt: SQLColumnExpression):

    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestParser:

    def test_encoded_spaces_in_value(self):
        params = {
            "test_column": "eq.test%20value"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column = 'test value'"

    def test_eq(self):

        params = {
            "test_column": "eq.test value"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column = 'test value'"

    def test_multiple_eq(self):

        params = {
            "test_column0": "eq.test value0",
            "test_column1": "eq.test value1",
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column0 = 'test value0' AND test_column1 = 'test value1'"

    def test_eq_int(self):
        """For this test there is no point to cast as postgres will do that on its side automatically"""

        params = {
            "test_column": "eq.1"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column = '1'"

    def test_like(self):

        params = {
            "test_column": "like.%its rock time%"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column LIKE '%its rock time%'"

    def test_encoded_like(self):

        params = {
            "test_column": "like.%its%20rock%20time%"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column LIKE '%its rock time%'"

    def test_is_null(self):

        params = {
            "test_column": "is.null"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column IS NULL"

    def test_is_true(self):

        params = {
            "test_column": "is.true"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column IS true"

    def test_is_false(self):

        params = {
            "test_column": "is.false"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column IS false"

    def test_is_not_null(self):

        params = {
            "test_column": "not.is.null"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column IS NOT NULL"

    def test_is_not_like(self):

        params = {
            "test_column": "not.like.%value%"
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params)

        assert compile_statement(sql) == "test_column NOT LIKE '%value%'"

    def test_period_in_string(self):

        params = {
            'test_column': 'like.%2.5 Ga to 3.2 Ga%'
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params.items(), Table("test_table", MetaData(), Column("test_column", String)))

        assert compile_statement(sql) == "test_table.test_column LIKE '%2.5 Ga to 3.2 Ga%'"

    def test_period_in_string(self):

        params = {
            'test_column': 'like.Felsic'
        }

        query_params = QueryParams(params)

        sql = query_parser(query_params.items(), Table("test_table", MetaData(), Column("test_column", String)))

        assert compile_statement(sql) == "test_table.test_column LIKE '%Felsic%'"