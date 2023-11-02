# Parser to handle filters on arbitrary fields
#
# Based on the PostgREST filter params:
# https://postgrest.org/en/stable/references/api/resource_embedding.html?highlight=filter#embedded-filters
#

import urllib.parse

import starlette.requests

from fastapi import FastAPI, HTTPException

from sqlalchemy.sql.expression import SQLColumnExpression
from sqlalchemy import and_, Column, not_, Table


class ParserException(Exception):
    pass


def cast_to_column_type(column: Column, value):
    try:
        return column.type.python_type(value)
    except Exception:
        raise ParserException(f"Value ({value}) could not be cast to appropriate python type ({column.type.python_type})")


# Expectation is that the query will be formatted like so
# field=eq.value
# which translates to
# field = 'value'
def get_column_expression(column: Column, operators, value: str):

    if len(operators) == 0:
        raise ParserException(f"Query parameters invalid")

    match operators[0]:

        case "not":
            return not_(get_column_expression(column, operators[1:], value))

        case "eq":
            value = cast_to_column_type(column, value)
            return column.__eq__(value)

        case "lt":
            value = cast_to_column_type(column, value)
            return column.__lt__(value)

        case "le":
            value = cast_to_column_type(column, value)
            return column.__le__(value)

        case "gt":
            value = cast_to_column_type(column, value)
            return column.__gt__(value)

        case "ge":
            value = cast_to_column_type(column, value)
            return column.__ge__(value)

        case "ne":
            value = cast_to_column_type(column, value)
            return column.__ne__(value)

        case "like":
            value = cast_to_column_type(column, value)
            return column.like(value)

        case "in":
            if value[0] != "(" or value[-1] != ")":
                raise ParserException(f"Query param value for in must be in form (x,y,z)")

            values = value[1:-1].split(",")
            clean_values = map(lambda x: cast_to_column_type(column, x), values)

            return column.in_(clean_values)

        case "is":
            if value.lower() == "false":
                return column.is_(False)
            elif value.lower() == "true":
                return column.is_(True)
            elif value.lower() == "null":
                return column.is_(None)
            else:
                raise ParserException(f"Query params outside valid set: {operators}")

        case "_":
            raise ParserException(f"Query params outside valid set: {operators}")


def query_parser(query_params: list, table: Table) -> SQLColumnExpression:

    column_expressions = []

    for column_name, encoded_expression in query_params:

        encoded_expression_split = encoded_expression.split(".")

        operators, value = encoded_expression_split[:-1], encoded_expression_split[-1]

        value = urllib.parse.unquote(value)

        column = table.c[column_name]

        column_expression = get_column_expression(column, operators, value)

        column_expressions.append(column_expression)

    if len(column_expressions) == 1:
        return column_expressions[0]

    else:
        return and_(*column_expressions)


