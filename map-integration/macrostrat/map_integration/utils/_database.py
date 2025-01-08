from macrostrat.database import Database


def table_exists(db: Database, table_name: str, schema: str = "public") -> bool:
    """Check if a table exists in a PostgreSQL database."""
    sql = """SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_name = :table_name
    );"""

    return db.run_query(sql, dict(schema=schema, table_name=table_name)).scalar()


def column_exists(db: Database, table_name, column_name, schema="public"):
    res = db.run_query(
        """
        SELECT count(*) FROM information_schema.columns c
        WHERE c.table_schema = :schema
          AND c.table_name = :table_name
          AND c.column_name = :column_name
        """,
        dict(
            schema=schema,
            table_name=table_name,
            column_name=column_name,
        ),
    )
    return res.scalar() == 1
