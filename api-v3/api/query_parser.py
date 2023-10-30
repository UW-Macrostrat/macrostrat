# Parser to handle filters on arbitrary fields
#
# Based on the PostgREST filter params:
# https://postgrest.org/en/stable/references/api/resource_embedding.html?highlight=filter#embedded-filters
#

import urllib.parse

import starlette.requests

from fastapi import FastAPI, HTTPException

from sqlalchemy.sql.expression import SQLColumnExpression
from sqlalchemy import and_, Column, not_


class ParserException(Exception):
    pass

# Expectation is that the query will be formatted like so
# field=eq.value
# which translates to
# field = 'value'

def get_column_expression(column_name, operators, value):

    if len(operators) == 0:
        raise ParserException(f"Query parameters invalid")

    match operators[0]:

        case "not":
            return not_(get_column_expression(column_name, operators[1:], value))

        case "eq":
            return Column(column_name).__eq__(value)

        case "lt":
            return Column(column_name).__lt__(value)

        case "le":
            return Column(column_name).__le__(value)

        case "gt":
            return Column(column_name).__gt__(value)

        case "ge":
            return Column(column_name).__ge__(value)

        case "ne":
            return Column(column_name).__ne__(value)

        case "like":
            return Column(column_name).like(value)

        case "is":
            if value.lower() == "false":
                return Column(column_name).is_(False)
            elif value.lower() == "true":
                return Column(column_name).is_(True)
            elif value.lower() == "null":
                return Column(column_name).is_(None)
            else:
                raise ParserException(f"Query params outside valid set: {operators}")

        case "_":
            raise ParserException(f"Query params outside valid set: {operators}")


def query_parser(query_params: starlette.requests.QueryParams) -> SQLColumnExpression:

    column_expressions = []

    for column_name, encoded_expression in query_params.items():

        encoded_expression_split = encoded_expression.split(".")

        operators, value = encoded_expression_split[:-1], encoded_expression_split[-1]
        value = urllib.parse.unquote(value)

        column_expression = get_column_expression(column_name, operators, value)

        column_expressions.append(column_expression)

    if len(column_expressions) == 1:
        return column_expressions[0]

    else:
        return and_(*column_expressions)


