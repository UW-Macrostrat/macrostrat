from ._test_helpers import lith_names_fixture
from .strat_names import (
    Confidence,
    StratNameTextMatch,
    StratRank,
    clean_strat_name,
)


def test_clean_strat_name():
    name = "Silverton Mountain Formation"
    res = clean_strat_name(name)
    assert len(res) == 1
    res = res[0]
    assert res.name == "silverton mountain"
    assert res.rank is StratRank.Formation


def test_clean_strat_name_lith():
    name = "Noonday Dolomite"
    res = clean_strat_name(name)
    assert len(res) == 1
    res = res[0]
    assert res.name == "noonday"
    assert res.rank is None


def test_clean_strat_name_hard():
    """Test strat name cleaning on a hard name (Wagon Bed Formation)"""

    name = "Wagon Bed Formation"
    res = clean_strat_name(name)
    assert len(res) == 1
    assert res[0].name == "wagon bed"
    assert res[0].rank == StratRank.Formation


def test_clean_strat_name_multiple():
    name = "Arikaree; Wagon Bed Formation; Supai Group"
    res = clean_strat_name(name)
    assert len(res) == 3
    assert res[0].name == "arikaree"
    assert res[0].rank is None

    assert res[1].name == "wagon bed"
    assert res[1].rank == StratRank.Formation

    assert res[2].name == "supai"
    assert res[2].rank == StratRank.Group


def test_hierarchy_is_off_by_default():
    """A nested name stays one name unless hierarchy splitting is asked for.

    `of` is in `stop_words` and the reset branch in `_clean_name` says it should
    end a name, but `build_ignore_list` puts stop words in the ignore list and the
    `continue` there fires first. The result runs both units together and keeps
    the article. Existing callers were written against this, so it is what the
    default still does.
    """
    name = "Williamson Creek Member of the Fleming Formation"
    res = clean_strat_name(name)
    assert len(res) == 1
    assert res[0].name == "williamson creek member the fleming"
    assert res[0].rank == StratRank.Formation


def test_hierarchy_splits_a_nested_name():
    """ "X Member of the Y Formation" names a unit and its parent, not one unit."""
    name = "Williamson Creek Member of the Fleming Formation"
    res = clean_strat_name(name, split_hierarchy=True)
    assert len(res) == 2

    # Yielded right-to-left, so the parent comes out first.
    assert res[0].name == "fleming"
    assert res[0].rank == StratRank.Formation
    assert res[1].name == "williamson creek"
    assert res[1].rank == StratRank.Member

    # `StratNameTextMatch.__lt__` orders by rank, so sorting puts the most
    # specific unit first -- which is the one a caller should prefer.
    assert sorted(res)[0].name == "williamson creek"


def test_hierarchy_drops_articles():
    """`the` is only ever exposed by a separator, so it is dropped in that mode."""
    name = "Kekiktuk Conglomerate of the Endicott Group"
    res = clean_strat_name(name, split_hierarchy=True)
    assert [r.name for r in res] == ["endicott", "kekiktuk"]
    assert res[0].rank == StratRank.Group
    # The conglomerate is a lithology, not part of the name, and is still ignored.
    assert res[1].rank is None


def test_hierarchy_leaves_unnested_names_alone():
    """Names with no separator parse identically either way.

    Worth pinning: "Wagon Bed Formation" is the case the right-to-left walk exists
    for, and hierarchy mode must not start treating `Bed` as a second name.
    """
    for name in [
        "Silverton Mountain Formation",
        "Noonday Dolomite",
        "Wagon Bed Formation",
        "Arikaree; Wagon Bed Formation; Supai Group",
    ]:
        assert clean_strat_name(name) == clean_strat_name(name, split_hierarchy=True)


def test_hierarchy_preserves_column_ingestion_spec_examples():
    """The spreadsheet spec's own strat_name examples must parse the same either way.

    `Code/column-ingestion/Format documentation.md` defines the canonical form:
    `,` separates child from parent within a chain, `;` separates distinct chains,
    most specific first. Those chains are split by `_split_names` before
    `_clean_name` ever sees them, so hierarchy mode should be a no-op on them --
    it exists for the prose form ("X Member *of the* Y Formation") that the spec
    does not cover.

    The `Bed A` and `A Member` cases are the load-bearing ones: the spec uses
    single-letter designations for informal units, so a parser that drops `a` as
    an article deletes the name instead of cleaning it.
    """
    examples = [
        "Molas Formation",
        "Alexandria Bay Gneiss, Piseco Group, Adirondack Supergroup",
        "Dry Creek Canyon Member, Dakota Sandstone; Burro Canyon Formation",
        "Lower Member, Ubisis Formation; Bed A, Ubisis Formation",
        "A Member, B Formation; C Member, B Formation, E Group; D Formation, E Group",
    ]
    for name in examples:
        assert clean_strat_name(name) == clean_strat_name(name, split_hierarchy=True)

    # And the single-letter names survive at all.
    res = clean_strat_name("Bed A, Ubisis Formation", split_hierarchy=True)
    assert (
        StratNameTextMatch(
            name="a", rank=StratRank.Bed, confidence=Confidence.NotIndicated
        )
        in res
    )


def test_hierarchy_keeps_an_article_that_is_part_of_the_name():
    """`The Forks` is a formation in the lexicon, so `the` is not always noise.

    Dropping it unconditionally cost a real SGMC match. An article is only
    noise where the grammar put it there -- directly after a separator, as in
    "of *the* Endicott Group" -- so that is the only place it comes out.
    """
    res = clean_strat_name("The Forks Formation", split_hierarchy=True)
    assert len(res) == 1
    assert res[0].name == "the forks"
    assert res[0].rank == StratRank.Formation

    # ...but still dropped where a separator exposed it.
    res = clean_strat_name(
        "Kekiktuk Conglomerate of the Endicott Group", split_hierarchy=True
    )
    assert [r.name for r in res] == ["endicott", "kekiktuk"]


def test_lith_signifiers_are_kept():
    """A name whose rank is carried by its lithology keeps that lithology.

    `Ravenswood Granodiorite` cleans to `ravenswood` with no rank, which is the
    same shape a stripped description leaves behind. The lithology is the only
    thing that still says this was a unit name.
    """
    (name,) = clean_strat_name("Ravenswood Granodiorite")
    assert name.name == "ravenswood"
    assert name.rank is None
    assert name.lith_signifiers == ["granodiorite"]


def test_lith_signifiers_distinguish_a_description():
    """The collision this exists to break."""
    (member,) = clean_strat_name("Gray Member")
    described = clean_strat_name("gray, medium-grained sandstone")
    assert member.name == "gray" and member.lith_signifiers == []
    # Same key, so the lexicon is reached either way -- but the clause that
    # reduced to `gray` carries no lithology to agree with.
    assert described[0].name == "gray"
    assert described[0].lith_signifiers == []


def test_lith_signifiers_exclude_grammar_and_position():
    """Stop words and positional terms share the ignore list but are not liths."""
    names = clean_strat_name(
        "Kekiktuk Conglomerate of the Endicott Group", split_hierarchy=True
    )
    by_name = {n.name: n for n in names}
    assert by_name["kekiktuk"].lith_signifiers == ["conglomerate"]
    assert by_name["endicott"].lith_signifiers == []
    (lower,) = clean_strat_name("Lower Chugwater Formation")
    assert lower.lith_signifiers == []


def test_lith_signifiers_do_not_affect_equality():
    """Adding the field must not change how matches compare or hash."""
    (a,) = clean_strat_name("Ravenswood Granodiorite")
    b = a.model_copy(update={"lith_signifiers": []})
    assert a == b
    assert hash(a) == hash(b)
