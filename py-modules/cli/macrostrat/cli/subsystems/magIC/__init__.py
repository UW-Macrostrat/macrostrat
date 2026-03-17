import requests
from datetime import datetime, timezone
from sqlalchemy import text
from macrostrat.match_utils import (
    get_columns_for_location,
    get_all_matched_units,
    standardize_names,
    get_units_without_col,
)
from macrostrat.match_utils import ColumnInfo
from macrostrat.match_utils.strat_names import create_ignore_list
from macrostrat.database import Database
from macrostrat.cli.database.utils import engine_for_db_name

API_DOMAIN = "https://api.earthref.org/v1/MagIC/search/sites"

def _float(val):
    if val is None:
        return None
    stripped = str(val).strip()
    return float(stripped) if stripped else None

def fetch_sites(published_since: str) -> list[dict]:
    """Paginate through the magIC API and return all site records."""
    sites = []
    params = {
        "published_since": published_since,
        "included_columns": ["dir_polarity"],
        "from": 1,
    }
    while True:
        response = requests.get(API_DOMAIN, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        print(params["from"], results[0].get("site"))
        sites.extend(results)
        total = data.get("total", 0)
        params["from"] += len(results)

        if params["from"] > total:
            break
    return sites


def map_site(site: dict, fetched_at: datetime) -> dict:
    """Map a raw magIC site record to the paleomag_sites schema."""
    lat = site.get("lat")
    lng = site.get("lon")
    #update citations to use this format https://dx.doi.org/10.7288/V4/MAGIC/{contribution_id}}
    return {
        "external_id": site.get("contribution_id"),
        "site_name": site.get("site"),
        "lat": _float(site.get("lat")),
        "lng": _float(site.get("lon")),
        "age_low": _float(site.get("age_low")), #add age and uncertainty fields. Only 3.6k sites have this populated.
        "age_high": _float(site.get("age_high")),#add age and uncertainty field. Only 3.6k sites have this populated.
        "age": _float(site.get("age")),
        "age_unit": site.get("age_unit"), #can have mapped units by strat name, or just map standalone ages alongside the column
        "lithologies": site.get("lithologies"),
        "formation": site.get("formation") or "",
        "dir_polarity": site.get("dir_polarity"), #can calc from inc and dec. Can get it from vgp_lat 45 to 90: normal, -45 to -90 reversed
        "dir_inc": _float(site.get("dir_inc")), #main fields inputted
        "dir_dec": _float(site.get("dir_dec")), #main fields inputted
        "dir_alpha95": _float(site.get("dir_alpha95")),
        "dir_k": _float(site.get("dir_k")),
        "dir_n_specimens_lines": _float(site.get("dir_n_specimens_lines")),
        "dir_tilt_correction": _float(site.get("dir_tilt_correction")),
        "vgp_lat": _float(site.get("vgp_lat")),
        "vgp_lon": _float(site.get("vgp_lon")),
        "last_updated": fetched_at,
        "citations": f"https://dx.doi.org/10.7288/V4/MAGIC/{site.get("contribution_id")}",
        "geometry": f"SRID=4326;POINT({site.get('lon')} {site.get('lat')})" if site.get("lat") and site.get("lon") else None,
    }


def load_sites(engine, rows: list[dict]) -> None:
    """
    Insert or update geomag_sites rows.
    load key: (external_id, site) — uniquely identifies a site.
    """
    load_sql = text("""
        INSERT INTO integrations.geomag_sites (
            external_id, site_name,
            lat, lng,
            age_low, age_high, age, age_unit,
            lithologies, formation,
            dir_polarity, dir_inc, dir_dec, dir_alpha95, dir_k, dir_n_specimens_lines, dir_tilt_correction, vgp_lat, vgp_lon,
            last_updated, created_at, citations, geometry
        ) VALUES (
            :external_id, :site_name,
            :lat, :lng,
            :age_low, :age_high,:age, :age_unit,
            :lithologies, :formation,
            :dir_polarity, :dir_inc, :dir_dec, :dir_alpha95, :dir_k, :dir_n_specimens_lines, :dir_tilt_correction, :vgp_lat, :vgp_lon,
            :last_updated, now(), :citations,
            CASE WHEN :geometry IS NOT NULL THEN ST_GeomFromEWKT(:geometry) END
        )
        ON CONFLICT (external_id, site)
        DO UPDATE SET
            lat                   = EXCLUDED.lat,
            lng                   = EXCLUDED.lng,
            age_low               = EXCLUDED.age_low,
            age_high              = EXCLUDED.age_high,
            age                   = EXCLUDED.age,
            age_unit              = EXCLUDED.age_unit,
            lithologies           = EXCLUDED.lithologies,
            formation             = EXCLUDED.formation,
            dir_polarity          = EXCLUDED.dir_polarity,
            dir_inc               = EXCLUDED.dir_inc,
            dir_dec               = EXCLUDED.dir_dec,
            dir_alpha95           = EXCLUDED.dir_alpha95,
            dir_k                 = EXCLUDED.dir_k,
            dir_n_specimens_lines = EXCLUDED.dir_n_specimens_lines,
            dir_tilt_correction   = EXCLUDED.dir_tilt_correction,
            vgp_lat               = EXCLUDED.vgp_lat,
            vgp_lon               = EXCLUDED.vgp_lon,
            last_updated          = EXCLUDED.last_updated,
            citations              = EXCLUDED.citations,
            geometry              = EXCLUDED.geometry
    """)

    with engine.begin() as conn:
        conn.execute(load_sql, rows)


def get_last_updated(engine) -> str:
    """Return the most recent last_updated timestamp for delta syncs."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT MAX(last_updated) FROM integrations.geomag_sites")
        ).scalar()
    return result.strftime("%Y-%m-%d") if result else "1900-01-01"


def run(published_since: str = None):
    engine = engine_for_db_name("macrostrat")
    print(engine.url)
    since = published_since or get_last_updated(engine)
    print(f"Fetching magIC sites published since {since}...")

    fetched_at = datetime.now(timezone.utc)
    sites = fetch_sites(since)
    print(f"Found {len(sites)} site records")

    rows = [map_site(s, fetched_at) for s in sites if s.get("site")]
    load_sites(engine, rows)
    print(f"Updated and inserted {len(rows)} rows into geomag_sites")


def get_formations_by_age_col(db, col_id: int | None, t_age: float | None, b_age: float | None) -> tuple:
    """
    Query macrostrat strat names associated with units in a given column
    that overlap the provided age range. Returns a standardized names tuple
    suitable for passing into get_matched_unit.

    Falls back to all units in the column if no age is provided.
    """
    params = {}
    age_filter = "AND lu.t_age <= :b_age AND lu.b_age >= :t_age"
    params["t_age"] = t_age
    params["b_age"] = b_age

    if col_id is not None:
        params = {"col_id": col_id}
        rows = db.run_query(
            f"""
            SELECT DISTINCT sn.strat_name
            FROM macrostrat.strat_names sn
            JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = sn.id
            JOIN macrostrat.units u ON u.id = usn.unit_id
            JOIN macrostrat.lookup_units lu ON lu.unit_id = u.id
            WHERE u.col_id = :col_id
              AND sn.strat_name IS NOT NULL
              AND sn.strat_name != ''
              {age_filter}
            """,
            params,
        ).all()
    else:
        rows = db.run_query(
            f"""
            SELECT DISTINCT sn.strat_name
            FROM macrostrat.strat_names sn
            JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = sn.id
            JOIN macrostrat.units u ON u.id = usn.unit_id
            JOIN macrostrat.lookup_units lu ON lu.unit_id = u.id
            WHERE sn.strat_name IS NOT NULL
              AND sn.strat_name != ''
              {age_filter}
            """,
            params,
        ).all()

    if not rows:
        return None

    # Join all names and run through the same cleaning pipeline
    # that get_matched_unit expects on the input side
    combined = "; ".join(row.strat_name for row in rows)
    return standardize_names(combined)


def get_nearest_column(db, lng: float, lat: float, max_distance_degrees: float = 1.0):
    """
    Fall back to nearest column when the point is not inside any column polygon.
    max_distance_degrees limits how far to search — 1 degree ~ 111km.
    """
    rows = db.run_query(
        """
        SELECT col_id, project_id, status_code,
               ST_Distance(ca.col_area, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) AS distance
        FROM macrostrat.col_areas ca
        JOIN macrostrat.cols c ON c.id = ca.col_id
        WHERE c.status_code = 'active'
          AND ST_DWithin(ca.col_area, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :max_dist)
        ORDER BY distance
        LIMIT 1
        """,
        dict(lng=lng, lat=lat, max_dist=max_distance_degrees),
    ).all()

    if not rows:
        return None
    return ColumnInfo.model_validate(rows[0])



def match_geomag_sites():
    """
    Query all geomag_sites from the database and match each to a Macrostrat column + unit.
    """
    engine = engine_for_db_name("macrostrat")
    db = Database(engine.url)

    #initialize ignore list once before matching
    lith_names = db.run_query("SELECT lith FROM macrostrat.liths").scalars().all()
    create_ignore_list(lith_names)

    sites = db.run_query(
        "SELECT id, site_name, lat, lng, formation, age, age_low, age_high FROM integrations.geomag_sites LIMIT 1000"
    ).all()

    print(f"Matching {len(sites)} geomag sites...")

    for site in sites:
        print(f"Matching......... {site.id}, {site.site_name}")
        if site.lat is None or site.lng is None:
            print(f"Skipping because there is no lat/lng {site.id}, {site.site_name}")
            continue

        lng = site.lng
        if lng > 180:
            lng -= 360


        #Resolve age bounds
        age = _float(site.age)
        age_low = _float(site.age_low)
        age_high = _float(site.age_high)

        if age_low is not None and age_high is not None:
            t_age = age_high
            b_age = age_low
        else:
            t_age = age
            b_age = age

        cols = get_columns_for_location(db, (lng, site.lat))
        if not cols:
            col = get_nearest_column(db, lng, site.lat)
            if col is not None:
                print(f"Using nearest column col_id={col.col_id} for site_id={site.id}")
        else:
            col = cols[0]

        # standardize formation name
        if not site.formation:
            names = get_formations_by_age_col(db, col.col_id if col else None, t_age, b_age)
            print(f"No formation name provided. Found formations by age: {names}")
            if names is None:
                print(f"Skipping because no macrostrat strat_names are found. {site.id}, {site.site_name}")
                continue
        else:
            names = standardize_names(site.formation)

        if col is None:
            print(f"No columns found for site_={site.site_name}. Finding units by age and formations.")
            unit = get_units_without_col(db, names, t_age, b_age)

        else:
        # Match unit
            with db.engine.connect() as conn:
                rows = get_all_matched_units(
                    conn,
                    col.col_id,
                    names,
                    t_age=t_age,
                    b_age=b_age,
                    n_results=1
                )
            unit = rows[0] if rows else None
        unit_id = unit.unit_id if unit is not None else None
        #TODO add age_span accuracy function to pick the "most correct" unit formation
        #TODO add units within the integrations.geomag_units table
        print(f"site_id={site.id} | col_id={col.col_id if col else None} | unit_id={unit_id} | strat_names='{names}' "
              f"| b_age={b_age} | t_age={t_age}")
        print("FINAL UNIT", unit)


if __name__ == "__main__":
    #run()
    match_geomag_sites()
