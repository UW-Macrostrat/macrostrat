"""Freeze legacy carto's prioritization into the compilations model.

The `carto` schema is built straight out of `maps.sources.display_scales`: a map
appears in a carto tier if it declares that scale, and the tier below it fills the
gaps from the next coarser scale. `display_scales` is an authored, multi-valued
list -- it is compilation membership already, stored on the map instead of as
edges -- so the whole of legacy carto's curation can be read back out and written
down in the model that replaced it.

Worth doing once, and soon. The extraction only works while `display_scales` and
the `carto` tables still exist, and both are transitional. It is also what lets
`maps.sources.new_priority` be retired: the one thing that column still expresses
that per-compilation priority does not is v1's ranking, and once that is written
down as `compilation_member.priority` there is nothing left for it to carry.
"""

from macrostrat.database import Database

#: The scale tiers legacy carto is built in, coarsest first.
TIERS = ("tiny", "small", "medium", "large")

#: What each carto tier draws on besides its own maps.
#:
#: A carto tier is filled from its own scale *and the next coarser one*, with the
#: coarser pass laid down first so an actual medium-scale map wins wherever it
#: covers and a small-scale map only shows through the gaps. That is gap-filling,
#: and in the compilations model it is not a ranking trick at all -- it is the
#: composition `carto-medium = {small, medium}` that the served carto layers
#: already use, with the coarser member at the lower priority.
UNDER = {"small": "tiny", "medium": "small", "large": "medium"}

#: The composite tiers, and the umbrella that names the whole snapshot.
COMPOSITES = ("small", "medium", "large")
UMBRELLA = "carto"


def slug_for(tier: str, suffix: str) -> str:
    return f"{tier}-{suffix}"


def plan(db: Database, suffix: str = "v1") -> dict[str, list]:
    """What each base tier would contain, without writing anything."""
    return {
        tier: db.run_query(
            """
            SELECT s.slug, coalesce(s.new_priority, 0) AS priority
            FROM maps.sources s
            JOIN map_bounds.map_area a ON a.source_id = s.source_id
            WHERE :tier = ANY(s.display_scales)
            ORDER BY 1
            """,
            dict(tier=tier),
        ).all()
        for tier in TIERS
    }


def _ensure_source(db: Database, slug: str, name: str, scale: str | None) -> int:
    db.run_query(
        """
        INSERT INTO maps.sources
          (slug, name, scale, new_priority, status_code, is_finalized)
        VALUES (:slug, :name, :scale::maps.map_scale, 0, 'active', false)
        ON CONFLICT (slug) DO NOTHING
        """,
        dict(slug=slug, name=name, scale=scale),
    )
    return db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug", dict(slug=slug)
    ).scalar()


def write(db: Database, suffix: str = "v1", log=None) -> dict[str, int]:
    """Create the snapshot. Idempotent: re-running refreshes membership in place.

    **Commits its own work.** `Database.run_query` runs on `db.session` and does
    not commit, and the migration runner never commits either -- SQL-file
    migrations only persist because `run_fixtures` goes through `run_sql_file`.
    So a Python-fixture migration that leaves the commit to its caller writes
    everything and discards it, reporting success. Committing here makes the
    function correct from both call sites.
    """
    say = log or (lambda *a: None)
    tiers = plan(db, suffix)
    ids = {}

    for tier, members in tiers.items():
        slug = slug_for(tier, suffix)
        source_id = _ensure_source(db, slug, f"{tier.title()} (carto {suffix})", tier)
        ids[tier] = source_id
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority, role)
            SELECT :compilation_id, s.source_id, v.priority, 'constituent'
            FROM (SELECT unnest(:slugs::text[]) AS slug,
                         unnest(:priorities::integer[]) AS priority) v
            JOIN maps.sources s ON s.slug = v.slug
            ON CONFLICT (compilation_id, member_id)
            DO UPDATE SET priority = EXCLUDED.priority
            """,
            dict(
                compilation_id=source_id,
                slugs=[m.slug for m in members],
                priorities=[m.priority for m in members],
            ),
        )
        say(f"[green]{slug}[/] [dim]#{source_id}[/] {len(members)} members")

    composite_ids = {}
    for tier in COMPOSITES:
        slug = f"{UMBRELLA}-{tier}-{suffix}"
        source_id = _ensure_source(db, slug, f"Carto {tier} ({suffix})", tier)
        composite_ids[tier] = source_id
        # Coarser member first, at the lower priority -- the composition the
        # served carto layers already use, and what legacy carto's two-pass fill
        # was expressing procedurally.
        for priority, member_tier in enumerate((UNDER[tier], tier), start=1):
            db.run_query(
                """
                INSERT INTO map_bounds.compilation_member
                  (compilation_id, member_id, priority)
                VALUES (:compilation_id, :member_id, :priority)
                ON CONFLICT (compilation_id, member_id)
                DO UPDATE SET priority = EXCLUDED.priority
                """,
                dict(
                    compilation_id=source_id,
                    member_id=ids[member_tier],
                    priority=priority,
                ),
            )
            say(
                f"[green]+[/] {slug} <- {slug_for(member_tier, suffix)} [dim]({priority})[/]"
            )

    # The umbrella. Not a priority stack -- its members are at three different
    # scales and never compete -- but a single handle for the snapshot, and the
    # thing whose existence says the extraction has already happened.
    umbrella = f"{UMBRELLA}-{suffix}"
    umbrella_id = _ensure_source(
        db, umbrella, f"Carto, as prioritized in {suffix}", None
    )
    for priority, tier in enumerate(COMPOSITES, start=1):
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority, role)
            VALUES (:compilation_id, :member_id, :priority, 'snapshot')
            ON CONFLICT (compilation_id, member_id)
            DO UPDATE SET priority = EXCLUDED.priority, role = EXCLUDED.role
            """,
            dict(
                compilation_id=umbrella_id,
                member_id=composite_ids[tier],
                priority=priority,
            ),
        )
    say(f"[green]{umbrella}[/] [dim]#{umbrella_id}[/] names the snapshot")
    db.session.commit()
    return {slug_for(t, suffix): len(m) for t, m in tiers.items()}
