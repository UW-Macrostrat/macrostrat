def create_macrostrat_isopach_map(strat_name: str):
    """Create a map of isopach data for a given stratigraphic unit"""
    print(f"Creating isopach map for {strat_name}")

    import geopandas as G

    df = G.read_file(
        "https://dev2.macrostrat.org/api/v2/columns?all&output_format=geojson_bare"
    )

    df["lon"] = df["geometry"].centroid.x
    df["lat"] = df["geometry"].centroid.y
    print(df)
