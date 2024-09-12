from json import dumps
from pathlib import Path

from requests import get
from rich import print
from typer import Typer

from ...database import SubsystemSchemaDefinition, get_db

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

kg_schema = SubsystemSchemaDefinition(
    name="knowledge-graph",
    fixtures=[fixtures_dir],
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
                "abstract": "<p>Segment 9, which consists of Minnesota, Iowa, Wisconsin, and Michigan, abuts the Canadian border in the upper Midwest and lies adjacent to or surrounds four of the Great Lakes-Superior, Michigan, Huron, and Erie. Thousands of small to large lakes similar to the one shown in figure 1 dot the landscape, which is drained by numerous rivers and streams tributary primarily to the Mississippi River in the west and to the Great Lakes-St. Lawrence River system in the east. These abundant surface-water sources represent an ample supply of water to large users, such as the cities of Milwaukee, Wis., and Detroit, Mich. However, water stored in unconsolidated and consolidated sedimentary-rock aquifers that underlie the four States also is in abundant supply and is an economical source that can be used for nearly any purpose, usually with little or no treatment. In more than 95 percent of the four-State area, these aquifers supply water to a broad spectrum of consumers-from individual households to cities, such as St. Paul, Minn., Madison, Wis., and Lansing, Mich. These aquifers are the subject of this chapter. The geology and the hydrology of each of the principal aquifers are illustrated and discussed insofar as information was available from the literature. Hydrogeology, ground-water flow, availability and quality of water, and freshwater withdrawals from each of the aquifers are the principal subjects of discussion. </p><p>Population in the four States is concentrated in the cities and is thinly dispersed in the broad agricultural areas of the States (fig. 2). Minneapolis-St. Paul, Minn., Des Moines, Iowa, Milwaukee and Madison, Wis., and Detroit and Lansing, Mich., are a few of the principal cities. Many of these cities and other large population centers represent areas of concentrated ground-water withdrawals. </p><p>Precipitation is the source of all water in Segment 9. Average annual precipitation ranges from about 20 to 40 inches across the segment and generally increases from northwest to southeast (fig. 3). Precipitation is least in the northwestern part of the segment because of the orographic effect of the Rocky Mountains, which are hundreds of miles to the west. Annual precipitation in excess of 36 inches that falls south and east of Lakes Superior and Michigan (fig. 3) is a result of the prevailing westerly winds that evaporate moisture from the lakes; this moisture subsequently condenses and falls as precipitation over the land. </p><p>Average annual runoff in rivers and streams (fig. 4) generally reflects average annual precipitation patterns (fig. 3). Runoff generally increases from less than 1 to more than 20 inches. Runoff also tends to be substantial downwind from Lakes Superior and Michigan. However, in no part of the segment does runoff exceed precipitation. Much of the water from precipitation is returned to the atmosphere by evapotranspiration-evaporation from the land and water surfaces, and transpiration by plants. Some of the water is stored in aquifers through ground-water recharge or is stored on the land surface in lakes, marshes, and reservoirs. Runoff represents water from precipitation that runs directly off the land surface to streams and water discharged to streams that was stored in lakes, marshes, reservoirs, or aquifers.</p>",
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
