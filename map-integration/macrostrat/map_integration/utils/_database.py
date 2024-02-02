from macrostrat.database import Database


def table_exists(db: Database, table_name: str, schema: str = "public") -> bool:
    """Check if a table exists in a PostgreSQL database."""
    sql = """SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = :schema
          AND table_name = :table_name
    );"""

    return db.run_query(sql, dict(schema=schema, table_name=table_name)).scalar()
