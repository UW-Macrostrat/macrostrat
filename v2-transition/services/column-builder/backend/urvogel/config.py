import os

db_name = os.environ.get("POSTGRES_DB", "column_data")
port = os.environ.get("PG_PORT", "5434")
user = os.environ.get("PGUSER", "postgres")

#postgresql://postgres@localhost:5434/column_data
pg_url = f"postgresql://{user}@localhost:{port}/{db_name}"