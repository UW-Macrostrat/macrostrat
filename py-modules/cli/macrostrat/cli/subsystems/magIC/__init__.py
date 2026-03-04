import requests
from datetime import datetime, timezone
from sqlalchemy import text

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

    return {
        "external_id": site.get("contribution_id"),
        "site_name": site.get("site"),
        "lat": _float(site.get("lat")),
        "lng": _float(site.get("lon")),
        "age_low": _float(site.get("age_low")),
        "age_high": _float(site.get("age_high")),
        "age_unit": site.get("age_unit"),
        "lithologies": site.get("lithologies"),
        "formation": site.get("formation") or "",
        "dir_polarity": site.get("dir_polarity"),
        "dir_inc": _float(site.get("dir_inc")),
        "dir_dec": _float(site.get("dir_dec")),
        "dir_alpha95": _float(site.get("dir_alpha95")),
        "dir_k": _float(site.get("dir_k")),
        "dir_n_specimens_lines": _float(site.get("dir_n_specimens_lines")),
        "dir_tilt_correction": _float(site.get("dir_tilt_correction")),
        "vgp_lat": _float(site.get("vgp_lat")),
        "vgp_lon": _float(site.get("vgp_lon")),
        "last_updated": fetched_at,
        "citations": site.get("citations") or "",
        "geometry": f"SRID=4326;POINT({site.get('lon')} {site.get('lat')})" if site.get("lat") and site.get("lon") else None,
    }


def load_sites(engine, rows: list[dict]) -> None:
    """
    Insert or update paleomag_sites rows.
    load key: (external_id, site_name) — uniquely identifies a site.
    """
    load_sql = text("""
        INSERT INTO integrations.paleomag_sites (
            external_id, site_name,
            lat, lng,
            age_low, age_high, age_unit,
            lithologies, formation,
            dir_polarity, dir_inc, dir_dec, dir_alpha95, dir_k, dir_n_specimens_lines, dir_tilt_correction, vgp_lat, vgp_lon,
            last_updated, created_at, citations, geometry
        ) VALUES (
            :external_id, :site_name,
            :lat, :lng,
            :age_low, :age_high, :age_unit,
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
            text("SELECT MAX(last_updated) FROM integrations.paleomag_sites")
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
    print(f"Updated and inserted {len(rows)} rows into paleomag_sites")


if __name__ == "__main__":
    run()