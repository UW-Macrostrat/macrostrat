# Parser to handle filters on arbitrary fields
#
# Based on the PostgREST filter params:
# https://postgrest.org/en/stable/references/api/resource_embedding.html?highlight=filter#embedded-filters
#

import urllib.parse
from dataclasses import dataclass

import starlette.requests
import logging
from fastapi import FastAPI, HTTPException, Request


from sqlalchemy.sql.expression import SQLColumnExpression
from sqlalchemy import and_, Column, not_, Table, func, distinct, cast, String

VALID_OPERATORS = ["not", "eq", "lt", "le", "gt", "ge", "ne", "like", "in", "is"]


log = logging.getLogger(__name__)


class ParserException(Exception):
    pass


def get_filter_query_params(request: Request) -> list[tuple[str, str]]:
    """Returns the query params that are not page or page_size"""

    return [*filter(lambda x: x[0] not in ["page", "page_size"], request.query_params.items())]


def cast_to_column_type(column: Column, value):
    try:
        return column.type.python_type(value)
    except Exception:
        raise ParserException(
            f"Value ({value}) could not be cast to appropriate python type ({column.type.python_type})"
        )


# Expectation is that the query will be formatted like so
# field=eq.value
# which translates to
# field = 'value'


@dataclass
class QueryParameter:
    column: Column
    operators: list[str]
    value: str


class QueryParser:
    """Used to parse the query parameters from the request"""

    VALID_OPERATORS = ["not", "eq", "lt", "le", "gt", "ge", "ne", "like", "in", "is"]

    def __init__(self, columns: list[Column], query_params: list[dict]):
        self.columns = {c.name: c for c in columns}
        self.query_params = query_params
        self.decomposed_query_params = self._decompose_query_params()

    def where_expressions(self):
        """Returns the where expressions for the query"""

        where_expressions = []

        for query_param in self.decomposed_query_params.values():
            if query_param.operators[0] not in ["group_by", "order_by"]:
                where_expressions.append(
                    self._get_operator_expression(
                        query_param.column, query_param.operators, query_param.value
                    )
                )

        if len(where_expressions) == 1:
            return where_expressions[0]

        else:
            return and_(*where_expressions)

    def get_group_by_column(self):
        """Returns the group by expressions for the query"""

        group_by_columns = []
        for query_param in self.decomposed_query_params.values():
            if query_param.operators[0] == "group_by":
                group_by_columns.append(query_param.column)

        if len(group_by_columns) > 1:
            raise ParserException(f"Only one group by expression is allowed")
        elif len(group_by_columns) == 0:
            return None

        return group_by_columns[0]

    def get_select_columns(self) -> list[Column]:
        """Returns the group by expression which does a string aggregation of distinct values in the other columns"""

        if self.get_group_by_column() is None:
            return [*self.columns.values()]

        columns = []
        for column in self.columns.values():
            if column.name == self.get_group_by_column().name:
                columns.append(column)
            else:
                columns.append(
                    func.STRING_AGG(distinct(cast(column, String)), ",").label(
                        column.name
                    )
                )

        return columns

    def get_order_by_columns(self):
        """Returns the order by expressions for the query"""

        order_by_columns = []

        for query_param in self.decomposed_query_params.values():
            if query_param.operators[0] == "order_by":
                order_by_columns.append(query_param.column)

        return order_by_columns

    def _decompose_query_params(self) -> dict:
        decomposed_query_params = {}

        for column_name, encoded_expression in self.query_params:
            operators, value = self._decompose_encoded_expression(encoded_expression)
            value = urllib.parse.unquote(value)

            col = self.columns.get(column_name, None)
            if col is None:
                # We should eventually make this an error
                log.warning(f"Column ({column_name}) not found in table")
                continue

            decomposed_query_params[column_name] = QueryParameter(
                column=col, operators=operators, value=value
            )

        return decomposed_query_params

    def _decompose_encoded_expression(self, encoded_expression) -> tuple:
        encoded_expression_split = encoded_expression.split(".")

        # If group_by or order_by, then there is no value
        if len(encoded_expression_split) == 1:
            if encoded_expression_split[0] not in ["group_by", "order_by"]:
                raise ParserException(f"Query is invalid.")

            return encoded_expression_split[:1], ""

        elif len(encoded_expression_split) == 2:
            return encoded_expression_split[:1], encoded_expression_split[1]

        else:
            if encoded_expression_split[0] == "not":
                if encoded_expression_split[1] in self.VALID_OPERATORS:
                    return encoded_expression_split[0:2], ".".join(
                        encoded_expression_split[2:]
                    )

                else:
                    raise ParserException(
                        f"Query is invalid. Use these Operators only {self.VALID_OPERATORS}"
                    )

            elif encoded_expression_split[0] in self.VALID_OPERATORS:
                return encoded_expression_split[:1], ".".join(
                    encoded_expression_split[1:]
                )

    @staticmethod
    def _get_operator_expression(column: Column, operators, value: str):
        if len(operators) == 0:
            raise ParserException(f"Query parameters invalid")

        match operators[0]:
            case "not":
                return not_(
                    QueryParser._get_operator_expression(column, operators[1:], value)
                )

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
                if value[0] != "%" or value[-1] != "%":
                    value = f"%{value}%"

                value = cast_to_column_type(column, value)
                return column.like(value)

            case "in":
                if value[0] != "(" or value[-1] != ")":
                    raise ParserException(
                        f"Query param value for in must be in form (x,y,z)"
                    )

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
                    raise ParserException(
                        f"Query params outside valid set: {operators}"
                    )

            case "_":
                raise ParserException(f"Query params outside valid set: {operators}")
