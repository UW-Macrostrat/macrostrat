from pathlib import Path

import numpy as N
from IPython import embed
from macrostrat.core.database import get_database
from pandas import read_csv, DataFrame


def ingest_strata_next(source: Path):
    src = Path(source)

    df = read_csv(src)
    # Set empty strings to NaN
    df.replace("", N.nan, inplace=True)

    # Get unique section IDs
    section_ids = df["section_id"].unique()

    print(f"Found {len(section_ids)} unique sections")

    db = get_database()
    project_id = get_or_create_project(db, "GBDB")

    for section_id in section_ids:
        df1 = df[df["section_id"] == section_id]
        ingest_column(df1)


def ingest_column(df: DataFrame):
    df2 = df.iloc[0]
    # Get the section name and other parameters

    embed()
    raise


def get_or_create_project(db, name: str):
    res = db.run_query(
        "SELECT id FROM macrostrat.projects WHERE project = :name",
        {"name": name},
    ).fetchone()
    if res is not None:
        return res
    res = db.run_query(
        "INSERT INTO macrostrat.projects (project) VALUES (:name) RETURNING id",
        {"name": name},
    ).fetchone()
    return res
