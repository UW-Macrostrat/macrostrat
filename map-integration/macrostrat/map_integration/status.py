from rich import print

from .utils.map_info import MapInfo, has_map_schema_data


def update_status_for_all_maps(db):
    """
    Check the status of a map.
    """
    # Get all map IDs
    maps = db.run_query(
        "SELECT source_id, slug FROM maps.sources ORDER BY source_id"
    ).all()

    print("Checking whether all maps have data in the [cyan]maps[/] schema...")

    for _map in maps:
        map_info = MapInfo(id=_map.source_id, slug=_map.slug)
        is_finalized = has_map_schema_data(db, map_info)

        db.run_query(
            "UPDATE maps.sources SET is_finalized = :is_finalized WHERE source_id = :map_id",
            dict(is_finalized=is_finalized, map_id=map_info.id),
        )

        _prt_val = "[green]finalized[/]" if is_finalized else "[yellow]not finalized[/]"

        print(f"#{map_info.id} {map_info.slug} is {_prt_val}")

    db.session.commit()
