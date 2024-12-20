import uuid

from geoalchemy2.shape import from_shape
from httpx import get
from shapely.geometry import shape

from macrostrat.core.database import get_database


def populate_strabospot():
    """Populate StraboSpot notable spots"""
    api = "https://strabospot.org/REST/notableSpots"
    db = get_database()
    # Todo: improve the model here.
    db.automap(schemas=["integrations"])
    model = db.model.integrations_dataset

    # Get or create type for general integrations
    type_id = db.run_query(
        """
        INSERT INTO integrations.dataset_type (name, organization)
        VALUES (:name, :organization)
        ON CONFLICT (name, organization)
        DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        dict(name="Notable spots", organization="StraboSpot"),
    ).scalar()

    assert type_id is not None

    # Right now, we have to reset the table before we can insert data
    db.run_sql(
        "DELETE FROM integrations.dataset WHERE type = :type_id",
        dict(type_id=type_id),
    )

    data = feature_iterator(api, type_id)

    insert_data(db, model, data)


def feature_iterator(base_url, type):
    """Iterate over features from the StraboSpot API"""
    for bbox_params in get_bbox_params():
        print(f"Getting data for {bbox_params}")
        data = get_data(base_url, bbox_params)
        print(f"   {len(data)} features")
        for feature in data:
            yield process_feature(feature, type)


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
            db.session.commit()
            to_insert = []
            print(f"Inserted {n_inserted} rows")
    if to_insert:
        db.session.bulk_insert_mappings(model, to_insert)
        db.session.commit()
        print(f"Inserted {n_inserted} rows")


def process_feature(feature, type):
    """Process a feature from the StraboSpot API"""
    # GeoJSON to WKB
    geom = shape(feature["geometry"]).centroid
    geom_wkb = from_shape(geom, srid=4326)
    props = feature["properties"]
    # hash ID to uuid
    # _id = props.get("id")

    return dict(
        geom=geom_wkb,
        uid=uuid.uuid4(),  # Ideally we'd do a better job of hashing the ID
        url=props.get("landing_page", None),
        type=type,
        name=props.get("name", None),
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
