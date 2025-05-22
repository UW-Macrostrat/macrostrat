import pandas as pd

from macrostrat.core.database import get_database


def japan_full_map(db, slug):
    df = pd.read_csv(
        "/Users/afromandi/Macrostrat/Maps/Japan/Japan Full/legend.tsv", sep="\t"
    )
    print("This is the head", df.head())
    table = f"sources.{slug}_polygons"
    # additional table file, and primary key field to join on that is in the file
    # make join a standard util function
    # ensure the resulting dataframe has a geom field

    db.run_sql(
        f"""ALTER TABLE {table}
    ADD COLUMN IF NOT EXISTS no INTEGER,
    ADD COLUMN IF NOT EXISTS symbol TEXT,
    ADD COLUMN IF NOT EXISTS r INTEGER,
    ADD COLUMN IF NOT EXISTS g INTEGER,
    ADD COLUMN IF NOT EXISTS b INTEGER,
    ADD COLUMN IF NOT EXISTS formationAge_ja TEXT,
    ADD COLUMN IF NOT EXISTS formationAge_en TEXT,
    ADD COLUMN IF NOT EXISTS group_ja TEXT,
    ADD COLUMN IF NOT EXISTS group_en TEXT,
    ADD COLUMN IF NOT EXISTS lithology_ja TEXT,
    ADD COLUMN IF NOT EXISTS lithology_en TEXT;
""",
        dict(table=table),
    )
    for _, row in df.iterrows():
        db.run_sql(
            f"""
                INSERT INTO {table} (
                    no, symbol, r, g, b,
                    formationAge_ja, formationAge_en,
                    group_ja, group_en,
                    lithology_ja, lithology_en
                ) VALUES (
                    %(no)s, %(symbol)s, %(r)s, %(g)s, %(b)s,
                    %(formationAge_ja)s, %(formationAge_en)s,
                    %(group_ja)s, %(group_en)s,
                    %(lithology_ja)s, %(lithology_en)s
                )
                """,
            row.to_dict(),
        )
    results = db.run_sql(f"SELECT * FROM {table} LIMIT 15")
    return print(results)


if __name__ == "__main__":
    db = get_database()
    japan_full_map(db, "japan_full_map")
