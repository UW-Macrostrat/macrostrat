import requests
from datetime import datetime, timezone
from sqlalchemy import text
from macrostrat.match_utils import (
    get_columns_for_location,
    get_all_matched_units,
    standardize_names,
    clean_strat_name_text,
    match_row
)
from macrostrat.match_utils import ColumnInfo
from macrostrat.match_utils.strat_names import create_ignore_list
from macrostrat.database import Database
from macrostrat.cli.database.utils import engine_for_db_name
from macrostrat.match_utils.models import MatchComparison
from pandas import read_sql

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
        ON CONFLICT (external_id, site_name)
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



def normalize_lithologies(known_liths, lithologies: str) -> list[str]:
    """
    Parse a geomag colon-separated lithology string and return only the
    lith names that exist in macrostrat.liths, normalized to lowercase.

    e.g. "Mudstone: Siltstone: Basalt" -> ["mudstone", "siltstone", "basalt"]
    """
    if not lithologies:
        return None
    input_liths = [l.strip().lower() for l in lithologies.split(":") if l.strip()]
    return [l for l in input_liths if l in known_liths]

def get_units_by_name_age_formation_col(
    db,
    col_id: int | None,
    t_age: float | None,
    b_age: float | None,
    lithologies: str | None = None,
    formation_names: tuple | None = None,  # add this
):
    params = {
        "col_id": col_id,
        "t_age": t_age,
        "b_age": b_age,
    }
    filters = [
        "sn.strat_name IS NOT NULL",
        "sn.strat_name != ''",
        "c.status_code = 'active'",
        "u.col_id = :col_id",
        "lu.t_age <= :t_age AND lu.b_age >= :b_age",
    ]

    # Filter by normalized formation names if provided
    if formation_names:
        name_strings = [n.name for n in formation_names]
        params["formation_names"] = name_strings
        filters.append("lower(sn.strat_name) = ANY(:formation_names)")

    lith_names = [l.strip().lower() for l in lithologies.split(":") if l.strip()]
    params["lith_names"] = lith_names
    lith_join = """
        JOIN macrostrat.unit_liths ul ON ul.unit_id = u.id
        JOIN macrostrat.liths l ON l.id = ul.lith_id
    """
    filters.append(
        "(lower(l.lith) = ANY(:lith_names) OR "
        "lower(l.lith_group::text) = ANY(:lith_names) OR "
        "lower(l.lith_type::text) = ANY(:lith_names) OR "
        "lower(l.lith_class::text) = ANY(:lith_names))"
    )

    where_clause = " AND ".join(filters)
    sql = f"""
        SELECT DISTINCT
            sn.id strat_name_id,
            sn.strat_name,
            sn.rank strat_rank,
            u.id unit_id,
            u.col_id,
            lu.t_age,
            lu.b_age
        FROM macrostrat.strat_names sn
        JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = sn.id
        JOIN macrostrat.units u ON u.id = usn.unit_id
        JOIN macrostrat.lookup_units lu ON lu.unit_id = u.id
        JOIN macrostrat.cols c ON c.id = u.col_id
        {lith_join}
        WHERE {where_clause}
    """
    with db.engine.connect() as conn:
        units_df =  read_sql(text(sql), conn, params=params)

    if units_df.empty:
        return None, None

    combined = "; ".join(units_df["strat_name"].dropna().unique())
    names = standardize_names(combined) if combined else None

    units_df["age_range"] = units_df["b_age"] - units_df["t_age"]
    unit = units_df.sort_values("age_range").iloc[0]

    return names, unit


# Custom mapping from geomag-specific terms to macrostrat lith/lith_type/lith_class/lith_group values
GEOMAG_LITH_MAP = {
    # Volcanic/igneous specific terms -> macrostrat lith_type or lith
    "tholeiite": "volcanic",
    "tholeiitic basalt": "basalt",
    "rhyolitic tuff": "tuff",
    "rhyolitic lava": "rhyolite",
    "basaltic lava": "basalt",
    "basaltic andesite": "andesite",
    "alkali basalt": "basalt",
    "felsic dike": "felsic",
    "mafic dike": "mafic",
    "mafic lava": "mafic",
    "felsic tuff": "tuff",
    "andesitic tuff": "tuff",
    "lapilli tephra": "tuff",
    "ignimbrite": "tuff",
    "hyaloclastite": "volcanic",
    "pyroclastite": "volcanic",
    "agglomerate": "volcanic",
    "extrusives": "volcanic",
    "intrusives": "plutonic",
    "felsite": "felsic",
    "feldspar porphyry": "felsic",
    "porphyry": "volcanic",
    "obsidian": "rhyolite",
    "dacite": "dacite",
    "rhyodacite": "rhyolite",
    "phonolite": "volcanic",
    "trachyte": "volcanic",
    "trachyandesite": "volcanic",
    "trachybasalt": "volcanic",
    "shoshonite": "volcanic",
    "latite": "volcanic",
    "quartz latite": "volcanic",
    "nepheline syenite": "syenite",
    "quartz syenite": "syenite",
    "monzodiorite": "diorite",
    "monzogabbro": "gabbro",
    "microgranite": "granite",
    "essexite": "gabbro",
    "shonkinite": "plutonic",
    "ijolite": "plutonic",
    "vogesite": "plutonic",
    "monchiquite": "plutonic",
    "lamprophyre": "plutonic",
    "pyroxenite": "plutonic",
    "carbonatite": "carbonate",
    "sandy limestone": "limestone",
    "mudstone": "mudstone",
    "siltstone": "siltstone",
    "not specified": None,
}


def normalize_lithologies_custom(lithologies: str) -> list[str] | None:
    """
    Fallback normalization for geomag lithology strings that don't match
    macrostrat lith names directly. Maps known geomag-specific terms to
    their closest macrostrat equivalent.

    Returns a list of normalized lith strings, or None if nothing maps.
    """
    if not lithologies:
        return None

    input_liths = [l.strip().lower() for l in lithologies.split(":") if l.strip()]
    mapped = []
    for lith in input_liths:
        mapped_val = GEOMAG_LITH_MAP.get(lith)
        if mapped_val is not None:
            mapped.append(mapped_val)

    return mapped if mapped else None

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
    known_liths_rows = db.run_query(
        "SELECT lith, lith_type, lith_class, lith_group FROM macrostrat.liths"
    ).all()
    known_liths = {
        val.lower()
        for row in known_liths_rows
        for val in (row.lith, row.lith_type, row.lith_class, row.lith_group)
        if val
    }
    sites = db.run_query(
        "SELECT id, site_name, lat, lng, formation, age, age_low, age_high, lithologies FROM integrations.geomag_sites LIMIT 1000"
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
            t_age = age_low #younger age
            b_age = age_high #older age
        else:
            t_age = age
            b_age = age

        cols = get_columns_for_location(db, (lng, site.lat))
        if not cols:
            col = get_nearest_column(db, lng, site.lat)
            if col is not None:
                print(f"Using nearest column col_id={col.col_id} for site_id={site.id}")
        else:
            col = cols[0] if cols else None

        units = None
        names = None
        lith_string = None
        #col_id and age
        #get formation names,lithologies
        if col is not None:
            normalized_liths = normalize_lithologies(known_liths, site.lithologies)
            if not normalized_liths:
                normalized_liths = normalize_lithologies_custom(site.lithologies)
            lith_string = ": ".join(normalized_liths) if normalized_liths else None
            if site.formation:
                names = standardize_names(site.formation)
            else:
                names = None
            names, units = get_units_by_name_age_formation_col(db, col.col_id, t_age, b_age, lith_string, names)

            """*
            with db.engine.connect() as conn:
                rows = get_all_matched_units(conn, col.col_id, names, t_age=t_age, b_age=b_age, n_results=1)
            print("Using get_all_matched_units!!!")
            unit = rows[0] if rows else None
            """

        #TODO add units within the integrations.geomag_units table

        # Fetch matched unit's lithologies for comparison
        unit_liths = None
        if units is not None:
            lith_rows = db.run_query(
                """
                SELECT l.lith, l.lith_type, l.lith_class, l.lith_group
                FROM macrostrat.unit_liths ul
                JOIN macrostrat.liths l ON l.id = ul.lith_id
                WHERE ul.unit_id = :unit_id
                """,
                dict(unit_id=int(units.unit_id)),
            ).all()
            unit_liths = ", ".join(r.lith for r in lith_rows) or "(none)"
        if units is not None:
            print("\n─── MATCH SUMMARY ───────────────────────────────────────")
            print(f"  site_id       : {site.id} | {site.site_name}")
            print(f"  --- INPUT ---")
            print(f"  formation     : {site.formation or '(none)'}")
            print(f"  lithologies   : {site.lithologies or '(none)'} → normalized: {lith_string or '(none)'}")
            print(f"  ages          : t_age={t_age} | b_age={b_age}")
            print(f"  lat/lng       : {site.lat}, {site.lng} → col_id={col.col_id if col else '(none)'}")
            print(f"  --- MATCH ---")
            print(f"  strat_name    : {units.strat_name}")
            print(f"  unit_id       : {units.unit_id}")
            print(f"  col_id        : {units.col_id}")
            print(f"  lithologies   : {unit_liths}")
            print(f"  ages          : t_age={units.t_age} | b_age={units.b_age}")
            # Age overlap quality
            if t_age is not None and b_age is not None:
                if t_age == b_age:
                    # Single point age — 100% if it falls within the unit range, 0% otherwise
                    score = 1.0 if units.t_age <= t_age <= units.b_age else 0.0
                else:
                    overlap = min(units.b_age, b_age) - max(units.t_age, t_age)
                    site_range = b_age - t_age
                    score = max(0.0, overlap / site_range)
                print(f"  age overlap   : {score:.0%}")
        else:
            print(f"  (no unit matched)")
        print("─────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    #run()
    match_geomag_sites()
