from .utils import get_sgp_samples, write_to_file
from geopandas import GeoDataFrame, sjoin
from macrostrat.cli.database import get_db
from sqlalchemy.sql import text
from pathlib import Path


def compute_paleo_positions(out_file: Path = None):
    """Compute paleogeographic positions for all SGP samples"""

    M = get_db()

    model_name = "Wright2013"

    model_id = M.run_query(
        "SELECT id FROM corelle.model WHERE name = :name", dict(name=model_name)
    ).scalar()

    # Plate polygons
    plates = GeoDataFrame.from_postgis(
        text(
            """SELECT
        geometry geom,
        plate_id,
        coalesce(old_lim, m.max_age) plate_max_age,
        coalesce(young_lim, m.min_age) plate_min_age
        FROM corelle.plate_polygon pp
        JOIN corelle.model m ON pp.model_id = m.id
        WHERE m.id = :model_id"""
        ),
        M.engine.connect(),
        params=dict(model_id=model_id),
    )

    samples = get_sgp_samples("paleogeography-samples")
    samples["plate_model"] = None

    # Spatial join of samples and plates
    samples = sjoin(samples, plates, how="left", op="intersects")
    samples.loc[samples["plate_id"].notnull(), "plate_model"] = model_name

    # Add columns
    samples["paleo_lat"] = None
    samples["paleo_lon"] = None

    # Rotate samples to paleogeographic positions
    n_total = len(samples["plate_id"].notnull())
    n_done = 0
    n_failed = 0
    for i, row in samples.iterrows():
        res = rotate_point(row)
        n_done += 1
        if res is None:
            n_failed += 1
        else:
            samples.loc[i, "paleo_lon"] = res[0]
            samples.loc[i, "paleo_lat"] = res[1]

        print(f"Processed {n_done} of {n_total} samples ({n_failed} failed)", end="\r")

    if out_file is not None:
        write_to_file(samples, out_file)
        return

    import IPython

    IPython.embed()


def rotate_point(row):
    from corelle.engine.rotate import get_plate_id, get_rotation, sph2cart, cart2sph, Q

    plate_id = row["plate_id"]

    age = row["interpreted_age"]
    model = row["plate_model"]

    if plate_id is None or age < row["plate_min_age"] or age > row["plate_max_age"]:
        return

    if row["geom"] is None:
        return

    point = (row["geom"].x, row["geom"].y)
    q = get_rotation(model, plate_id, age, safe=False)
    if q is None:
        return
    if q.w == 1:
        return

    v0 = sph2cart(*point)
    v1 = Q.rotate_vectors(q, v0)
    x, y = cart2sph(v1)
    return x, y
