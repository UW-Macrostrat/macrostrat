from json import dumps
from pathlib import Path

from requests import get
from rich import print
from typer import Typer

from ..macrostrat_api import setup_postgrest_access
from ...database import SubsystemSchemaDefinition, get_db
from ...database.utils import grant_permissions, grant_schema_ownership

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"


xdd_schema = SubsystemSchemaDefinition(
    name="xdd",
    fixtures=[
        fixtures_dir / "kg-views.sql",
        setup_postgrest_access("macrostrat_xdd"),
        grant_schema_ownership("macrostrat_xdd", "xdd-writer"),
        grant_permissions(
            "macrostrat_xdd", "web_admin", ["SELECT", "UPDATE"], tables=["source_text"]
        ),
    ],
)

text_vector_schema = SubsystemSchemaDefinition(
    name="vectors",
    fixtures=[
        fixtures_dir / "text-vectors.sql",
        grant_schema_ownership("text_vectors", "xdd-writer"),
        # Needed for tileserver to read the schema
        grant_permissions("text_vectors", "macrostrat", "ALL"),
    ],
)


cli = Typer(no_args_is_help=True)


@cli.command()
def cache_citations():
    """Cache citation information for publications from xDD"""

    db = get_db()
    # Find papers that are in the source_text table but not in the publication table
    paper_ids = db.run_query(
        "SELECT DISTINCT paper_id FROM macrostrat_xdd.source_text EXCEPT SELECT paper_id FROM macrostrat_xdd.publication"
    )

    for i, paper_id in enumerate(paper_ids.scalars()):
        # Query the xDD API for the paper's citation information
        print(paper_id)
        ref = get(f"https://xdd.wisc.edu/api/articles", params={"docid": paper_id})

        try:
            data = ref.json()
            bibjson = construct_bibjson(data)
            doi = find_doi(bibjson)
            url = find_link(bibjson)
        except Exception as e:
            print(f"Error processing paper {paper_id}: {e}")
            continue

        # Insert the citation into the database
        db.run_query(
            "INSERT INTO macrostrat_xdd.publication (paper_id, doi, url, citation) VALUES (:paper_id, :doi, :url, :citation)",
            dict(
                paper_id=paper_id,
                doi=doi,
                url=url,
                citation=dumps(bibjson),
            ),
        )
        if i % 10 == 0:
            db.session.commit()
        db.session.commit()


example_res = {
    "success": {
        "v": 2,
        "data": [
            {
                "type": "fulltext",
                "_gddid": "5d4f14bb0b45c76cafa453bc",
                "title": "Ground Water Atlas of the United States: Segment 9, Iowa, Michigan, Minnesota, Wisconsin",
                "volume": "",
                "journal": "Hydrologic Atlas",
                "link": [
                    {
                        "url": "https://pubs.usgs.gov/ha/ha730/ch_j/index.html",
                        "type": "publisher",
                    }
                ],
                "publisher": "U.S. Geological Survey",
                "abstract": "Test abstract",
                "author": [{"name": "Olcott, Perry G."}],
                "pages": "J1--J31",
                "number": "",
                "identifier": [{"type": "doi", "id": "10.3133/ha730J"}],
                "year": "1992",
            }
        ],
        "hits": 1,
        "license": "https://creativecommons.org/licenses/by-nc/2.0/",
    }
}


def construct_bibjson(ref):
    """Construct a bibjson object from a reference object
    Note: we haven't rigorously checked this against the spec yet.
    But it's fine for now...
    """
    assert ref["success"]["hits"] == 1
    data = ref["success"]["data"][0]
    data["xdd_id"] = data.pop("_gddid")
    data.pop("abstract", None)
    return data


def find_doi(bibjson):
    if "identifier" not in bibjson:
        return None
    for ident in bibjson["identifier"]:
        if ident["type"] == "doi":
            return ident["id"]
    return None


def find_link(bibjson):
    if "link" not in bibjson:
        return None
    for link in bibjson["link"]:
        if link["type"] == "publisher":
            return link["url"]
    return None
