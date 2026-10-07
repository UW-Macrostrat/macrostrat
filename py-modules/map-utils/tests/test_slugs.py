from pytest import mark, raises

from macrostrat.map_utils.slugs import (
    InvalidSlug,
    check_slug,
    selector,
    slugify,
    staging_table,
    table_prefix,
)


@mark.parametrize(
    "name, slug",
    [
        ("arizona_adamsmesa", "arizona-adamsmesa"),
        ("arizona_mine mountain", "arizona-mine-mountain"),
        ("arizona_saddlemountain.gdb", "arizona-saddlemountain-gdb"),
        ("umn-usc-_169_34067", "umn-usc-169-34067"),
        ("uncharted_points_only__22253", "uncharted-points-only-22253"),
        ("Geology 1:100,000", "geology-1-100-000"),
        ("ngs-alaska", "ngs-alaska"),
    ],
)
def test_slugify(name, slug):
    assert slugify(name) == slug
    assert check_slug(slug) == slug


@mark.parametrize("slug", ["japan_kyoto", "Japan", "a--b", "-a", "a-", ""])
def test_check_refuses(slug):
    with raises(InvalidSlug):
        check_slug(slug)


def test_tables_take_underscores():
    assert table_prefix("az-littlehorn-100k") == "az_littlehorn_100k"
    assert staging_table("az-littlehorn-100k", "lines") == "az_littlehorn_100k_lines"
    # A shared staging prefix passes through
    assert staging_table("ngs", "polygons") == "ngs_polygons"
    with raises(ValueError):
        staging_table("a", "linework")


def test_selector_reads_old_names():
    assert selector("japan_*") == "japan-*"
    assert (
        selector("arizona_adgm_1657818658314_498") == "arizona-adgm-1657818658314-498"
    )
