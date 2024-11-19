from geoalchemy2.shape import from_shape
from httpx import get
from shapely.geometry import shape
from typer import Typer

from macrostrat.core.database import get_database
from macrostrat.core.migrations import run_migrations
from .schema import StrabospotBaseSchema

app = Typer(
    no_args_is_help=True,
    help="StraboSpot structural geology data system",
)


@app.command()
def migrate(
    apply: bool = False,
    force: bool = False,
    data_changes: bool = False,
):
    """Run migrations for the StraboSpot integration"""
    run_migrations(
        subsystem="strabospot-integration",
        apply=apply,
        force=force,
        data_changes=data_changes,
    )


@app.command()
def populate():
    """Populate the StraboSpot database"""
    api = "https://strabospot.org/REST/notableSpots"
    db = get_database()
    # Todo: improve the model here.
    db.automap(schemas=["strabospot"])
    model = db.model.strabospot_featured_spots

    # Right now, we have to reset the table before we can insert data
    db.run_sql("TRUNCATE TABLE strabospot.featured_spots")

    data = feature_iterator(api)

    insert_data(db, model, data)


def feature_iterator(base_url):
    """Iterate over features from the StraboSpot API"""
    for bbox_params in get_bbox_params():
        print(f"Getting data for {bbox_params}")
        data = get_data(base_url, bbox_params)
        print(f"   {len(data)} features")
        for feature in data:
            yield process_feature(feature)


def insert_data(db, model, data):
    """Insert data into the StraboSpot database"""
    # map the table

    n_inserted = 0
    # Insert by 100-row chunks
    to_insert = []
    for row in data:
        n_inserted += 1
        to_insert.append(row)
        if len(to_insert) == 100:
            db.session.bulk_insert_mappings(model, to_insert)
            db.sesion.commit()
            to_insert = []
            print(f"Inserted {n_inserted} rows")
    if to_insert:
        db.session.bulk_insert_mappings(model, to_insert)
        db.session.commit()
        print(f"Inserted {n_inserted} rows")


def process_feature(feature):
    """Process a feature from the StraboSpot API"""
    # GeoJSON to WKB
    geom = shape(feature["geometry"]).centroid
    geom_wkb = from_shape(geom, srid=4326)
    props = feature["properties"]
    return dict(
        geom=geom_wkb,
        spot_id=props.get("id"),
        created_at=props.get("date"),
        data=props,
    )


def get_data(base_url, bbox):
    """Get data from the StraboSpot API"""
    res = get(base_url, params=bbox)
    data = res.json()
    # Check that we have a feature collection
    assert data["type"] == "FeatureCollection"
    return data["features"]


def get_bbox_params(interval=60):
    for lat_0 in range(-90, 90, interval):
        for lon_0 in range(-180, 180, interval):
            lat_1 = lat_0 + interval
            lon_1 = lon_0 + interval

            yield dict(
                xmin=lon_0,
                ymin=lat_0,
                xmax=lon_1,
                ymax=lat_1,
            )
