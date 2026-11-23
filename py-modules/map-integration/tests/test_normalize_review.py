"""The parts of `normalize review-points`, `review-layers` and the GeMS ingest
that need no database. Cases are from the Arizona maps of November 2026."""

import pandas as pd
import pytest

from macrostrat.map_integration.commands.review_layers import ilike_literal
from macrostrat.map_integration.commands.review_points import (
    CLEAR,
    fit,
    review_point,
)
from macrostrat.map_integration.utils.feature_text import pertinent
from macrostrat.map_integration.utils.gems_utils import (
    infer_line_types,
    match_legend_codes,
)

#: Sullivan Butte: 118 characters, which maps.points.point_type cannot hold.
LONG_TYPE = (
    "approximate plunge direction of inclined generic(origin or type not known "
    "or specified) lineation or linear structure "
)


def test_fit_drops_asides_then_words():
    assert fit(LONG_TYPE.strip()) == (
        "approximate plunge direction of inclined generic lineation or linear structure"
    )
    assert fit("bedding") == "bedding"
    assert len(fit("word " * 40)) <= 100


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Not assigned.", None),
        ("{0F1A2B3C-0000-1111-2222-333344445555}", None),
        ("1.1.1", None),
        ("import from CAF 2005", None),
        ("contact, approximately located", "contact, approximately located"),
    ],
)
def test_pertinent(value, expected):
    assert pertinent(value) == expected


def test_review_point_fills_blanks_and_keeps_values():
    new, _ = review_point(
        dict(
            type="bedding",
            azimuth=182,
            inclination=42,
            identityconfidence="certain",
            point_type=None,
            strike=None,
            dip=None,
            certainty=None,
        )
    )
    assert new["point_type"] == "bedding"
    assert (new["strike"], new["dip"]) == ("182", "42")
    assert new["certainty"] == "certain"

    kept, _ = review_point(dict(point_type="foliation", type="bedding", certainty="x"))
    assert kept["point_type"] == "foliation"
    assert kept["certainty"] == "x"


def test_review_point_clears_out_of_range():
    new, issues = review_point(dict(strike=555, dip=410, dip_dir=-5, azimuth=-999))
    assert new["strike"] == CLEAR
    assert new["dip"] == CLEAR
    assert new["dip_dir"] == CLEAR
    assert any(
        issue == "strike placeholder or out of range" for _, issue, _, _ in issues
    )

    # A dip of 0 is a value, not a blank.
    zero, _ = review_point(dict(strike=0, dip=0))
    assert (zero["strike"], zero["dip"]) == ("0", "0")


def test_review_point_fits_long_type_and_keeps_it_in_descrip():
    new, _ = review_point(
        dict(type=LONG_TYPE, point_type=LONG_TYPE, descrip=LONG_TYPE.strip())
    )
    assert len(new["point_type"]) <= 100
    assert new["descrip"] == LONG_TYPE.strip()


def test_match_legend_codes():
    legend = ["J^s", "Tc", "Qy", "K_a", "K|a"]
    found = match_legend_codes(["J²s", "Tc?", "Qy", "K~a", "Zz"], legend)
    assert found == {
        "J²s": ("J^s", "age-font character"),
        "Tc?": ("Tc", "queried code"),
    }
    # K~a matches two legend codes, so neither; Qy is exact; Zz has none.


def test_infer_line_types():
    rows = [("ContactsAndFaults", 3, "contact", "Contact")] * 9
    rows += [("ContactsAndFaults", 3, "fault", "Fault")]
    rows += [("ContactsAndFaults", 3, None, None)] * 4
    # Same rule id in another layer: a different rule.
    rows += [("GeologicLines", 3, None, None)] * 2
    # Too few typed lines on rule 7.
    rows += [("ContactsAndFaults", 7, "fault", "Fault")] * 2
    rows += [("ContactsAndFaults", 7, None, None)]
    # No rule.
    rows += [("ContactsAndFaults", -1, None, None)]
    df = pd.DataFrame(rows, columns=["source_layer", "ruleid", "type", "descrip"])
    df, typed = infer_line_types(df)
    assert typed == 4
    assert (df.loc[10:13, "type"] == "contact").all()
    # 9 of the rule's 10 typed lines agree on the description too: 90%.
    assert (df.loc[10:13, "descrip"] == "Contact").all()
    assert df.loc[14:15, "type"].isna().all()
    assert pd.isna(df.loc[18, "type"]) and pd.isna(df.loc[19, "type"])


def test_ilike_literal():
    assert ilike_literal("Map_Unit%Polys") == r"Map\_Unit\%Polys"


def test_review_line():
    from macrostrat.map_integration.commands.review_lines import review_line

    new, issues = review_line(
        dict(
            type="fault",
            identityconfidence="certain",
            notes="Buckskin-Rawhide detachment fault, ball on downthrown side",
            isconcealed="Y",
            certainty=None,
            name=None,
            direction=None,
        )
    )
    assert new["certainty"] == "certain"
    assert new["name"] == "Buckskin-Rawhide detachment fault"
    assert "downthrown" in new["descrip"] and new["descrip"].endswith("(concealed)")
    assert new["type"] == "fault"

    kept, issues = review_line(
        dict(certainty="approximate", notes="right-lateral fault")
    )
    assert kept["certainty"] == "approximate"
    assert kept["direction"] == "right-lateral"

    both, issues = review_line(dict(notes="dextral", label="left-lateral"))
    assert both["direction"] is None
    assert any(issue == "conflicting directions" for _, issue, _, _ in issues)


def test_type_from_rules():
    from macrostrat.map_integration.commands.review_lines import type_from_rules

    lines = [dict(source_layer="CAF", ruleid=3, type="contact", descrip="Contact")] * 5
    lines = [dict(line) for line in lines] + [
        dict(source_layer="CAF", ruleid=3, type=None, descrip=None)
    ]
    type_from_rules(lines)
    assert lines[-1]["type"] == "contact"
    assert lines[-1]["descrip"] == "Contact"
