"""Authoring the compilation graph: membership, priority and a source's own flags.

The same writes as `macrostrat compilations add | rm` and the raw `is_served` and
`superseded_by` updates, batched so a client can stage a set of edits and apply them
at once. The batch says exactly what should stand afterwards; nothing is inferred
here. In particular the CLI's reparenting -- withdrawing a member's direct edge
into a layer it now reaches through the compilation -- is the client's to put in
the batch, so that the removal is visible before it is saved.

Nothing downstream is rebuilt. `macrostrat topo update` is the one command after
any edit, and it takes long enough (a recompile of `medium` alone is ~20 s) that
it does not belong in a request.
"""

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

from .models import EdgeChange, EditRequest, EditResult, PropertyChange


async def apply_edits(conn: AsyncConnection, request: EditRequest) -> EditResult:
    """Apply a batch in the caller's transaction, raising to roll it back."""
    source_ids = {e.source_id for e in request.edits}
    for edit in request.edits:
        for m in edit.members or []:
            source_ids.add(m.member_id)
        if edit.superseded_by is not None:
            source_ids.add(edit.superseded_by)
    sources = await _sources(conn, list(source_ids))

    missing = sorted(source_ids - sources.keys())
    if missing:
        raise HTTPException(404, f"No maps with source ids {missing}")

    properties = []
    for edit in request.edits:
        properties += await _set_properties(conn, edit, sources[edit.source_id])
        properties += await _set_superseded_by(conn, edit, sources)
    await _refuse_supersession_cycles(conn, [p.source_id for p in properties])

    removed, changed, added = await _membership_changes(conn, request, sources)

    if not request.force:
        _refuse_superseded(added, sources)

    # Removals first: a batch that reverses a membership (A in B becomes B in A)
    # would otherwise trip the cycle check on the insert before the delete.
    for c in removed:
        await conn.execute(
            text(
                "DELETE FROM map_bounds.compilation_member"
                " WHERE compilation_id = :compilation_id AND member_id = :member_id"
            ),
            c.model_dump(include={"compilation_id", "member_id"}),
        )
    for c in changed:
        await conn.execute(
            text(
                "UPDATE map_bounds.compilation_member SET priority = :priority"
                " WHERE compilation_id = :compilation_id AND member_id = :member_id"
            ),
            c.model_dump(include={"compilation_id", "member_id", "priority"}),
        )
    try:
        for c in added:
            await conn.execute(
                text(
                    "INSERT INTO map_bounds.compilation_member"
                    " (compilation_id, member_id, priority)"
                    " VALUES (:compilation_id, :member_id, :priority)"
                ),
                c.model_dump(include={"compilation_id", "member_id", "priority"}),
            )
    except DBAPIError as err:
        # `check_compilation_member` refuses a cycle; its message names the pair.
        if "cycle" in str(err.orig):
            raise HTTPException(409, str(err.orig).splitlines()[0])
        raise

    await _refuse_crowded_scales(conn, added)

    return EditResult(edges=removed + changed + added, properties=properties)


async def _sources(conn: AsyncConnection, source_ids: list[int]) -> dict[int, dict]:
    res = await conn.execute(
        text(
            """
            SELECT s.source_id, s.slug, s.name, s.is_served,
              s.superseded_by AS superseded_by_id,
              sup.slug AS superseded_by
            FROM maps.sources s
            LEFT JOIN maps.sources sup ON sup.source_id = s.superseded_by
            WHERE s.source_id = ANY(:source_ids)
            """
        ),
        {"source_ids": source_ids},
    )
    return {row["source_id"]: dict(row) for row in res.mappings()}


async def _set_properties(conn: AsyncConnection, edit, source: dict):
    changes = []

    for field in ("is_served", "name"):
        value = getattr(edit, field)
        if value is None or value == source[field]:
            continue
        # The column name is one of the two literals above, never user input.
        await conn.execute(
            text(f"UPDATE maps.sources SET {field} = :value WHERE source_id = :id"),
            {"value": value, "id": edit.source_id},
        )
        changes.append(
            PropertyChange(
                source_id=edit.source_id,
                slug=source["slug"],
                field=field,
                value=value,
                previous=source[field],
            )
        )

    return changes


async def _set_superseded_by(conn: AsyncConnection, edit, sources: dict):
    """Supersession is advisory: it marks the map and deletes nothing. Removing
    the map from its compilations is a separate, explicit part of the batch."""
    if "superseded_by" not in edit.model_fields_set:
        return []
    source = sources[edit.source_id]
    value = edit.superseded_by
    if value == source["superseded_by_id"]:
        return []
    if value == edit.source_id:
        raise HTTPException(409, f"{source['slug']} cannot supersede itself")

    await conn.execute(
        text("UPDATE maps.sources SET superseded_by = :value WHERE source_id = :id"),
        {"value": value, "id": edit.source_id},
    )
    return [
        PropertyChange(
            source_id=edit.source_id,
            slug=source["slug"],
            field="superseded_by",
            value=value,
            previous=source["superseded_by_id"],
        )
    ]


async def _refuse_supersession_cycles(conn: AsyncConnection, source_ids: list[int]):
    """A chain of supersession must end. Checked after the batch's writes, so two
    edits that together close a loop are caught as well as one that does."""
    if not source_ids:
        return
    res = await conn.execute(
        text(
            """
            WITH RECURSIVE chain AS (
              SELECT source_id AS start, superseded_by AS next, 1 AS depth
              FROM maps.sources
              WHERE source_id = ANY(:ids) AND superseded_by IS NOT NULL
              UNION ALL
              SELECT c.start, s.superseded_by, c.depth + 1
              FROM chain c
              JOIN maps.sources s ON s.source_id = c.next
              WHERE s.superseded_by IS NOT NULL
                AND c.next <> c.start
                AND c.depth < 1000
            )
            SELECT s.slug FROM chain c
            JOIN maps.sources s ON s.source_id = c.start
            WHERE c.next = c.start
            LIMIT 1
            """
        ),
        {"ids": source_ids},
    )
    slug = res.scalar()
    if slug is not None:
        raise HTTPException(
            409, f"Supersession would loop back to {slug}; a chain must end"
        )


async def _membership_changes(conn: AsyncConnection, request: EditRequest, sources):
    """Each edited member list against the edges that stand now."""
    removed, changed, added = [], [], []

    for edit in request.edits:
        if edit.members is None:
            continue
        c_id = edit.source_id

        res = await conn.execute(
            text(
                "SELECT cm.member_id, cm.priority, s.slug"
                " FROM map_bounds.compilation_member cm"
                " JOIN maps.sources s ON s.source_id = cm.member_id"
                " WHERE cm.compilation_id = :id"
            ),
            {"id": c_id},
        )
        rows = res.mappings().all()
        current = {r["member_id"]: r["priority"] for r in rows}
        # A removed member is in none of the batch's lists, so not in `sources`.
        slugs = {r["member_id"]: r["slug"] for r in rows}
        wanted = {m.member_id: m.priority for m in edit.members}

        def change(member_id, kind, priority=None, previous=None):
            return EdgeChange(
                compilation_id=c_id,
                compilation_slug=sources[c_id]["slug"],
                member_id=member_id,
                member_slug=slugs.get(member_id) or sources[member_id]["slug"],
                change=kind,
                priority=priority,
                previous_priority=previous,
            )

        for member_id, priority in current.items():
            if member_id not in wanted:
                removed.append(change(member_id, "removed", previous=priority))
            elif wanted[member_id] != priority:
                changed.append(
                    change(member_id, "reprioritized", wanted[member_id], priority)
                )
        for member_id, priority in wanted.items():
            if member_id not in current:
                added.append(change(member_id, "added", priority))

    return removed, changed, added


async def _refuse_crowded_scales(conn: AsyncConnection, added: list[EdgeChange]):
    """A multiscale compilation has at most one member per scale, which
    `serving_source` hands a zoom to. Checked against the added edges once they
    are written, so a batch may swap a scale's member in one go; a conflict that
    already stood is `lint`'s to report, not a reason to refuse other edits."""
    if not added:
        return
    res = await conn.execute(
        text(
            """
            SELECT c.slug AS compilation, m.scale,
              string_agg(o.slug, ', ' ORDER BY o.slug) AS members
            FROM unnest(CAST(:compilations AS integer[]), CAST(:members AS integer[]))
              AS a(compilation_id, member_id)
            JOIN maps.sources c ON c.source_id = a.compilation_id
            JOIN maps.sources m ON m.source_id = a.member_id
            JOIN map_bounds.compilation_member cm
              ON cm.compilation_id = a.compilation_id
            JOIN maps.sources o
              ON o.source_id = cm.member_id AND o.scale IS NOT DISTINCT FROM m.scale
            WHERE map_bounds.is_multiscale(a.compilation_id)
            GROUP BY c.slug, m.scale
            HAVING count(*) > 1 OR m.scale IS NULL
            """
        ),
        {
            "compilations": [c.compilation_id for c in added],
            "members": [c.member_id for c in added],
        },
    )
    problems = []
    for r in res.mappings():
        if r["scale"] is None:
            reason = "a member of a multiscale compilation needs a scale"
        else:
            reason = f"more than one member at scale {r['scale']}"
        problems.append(
            {"compilation": r["compilation"], "member": r["members"], "reason": reason}
        )
    if problems:
        raise HTTPException(
            409,
            {
                "message": "A multiscale compilation takes one member per scale.",
                "problems": problems,
            },
        )


def _refuse_superseded(added: list[EdgeChange], sources: dict[int, dict]):
    """The CLI's member check: curation should be deliberate, so a superseded
    member is refused unless the batch says `force`."""
    problems = [
        {
            "compilation": c.compilation_slug,
            "member": c.member_slug,
            "reason": f"superseded by {sources[c.member_id]['superseded_by']}",
        }
        for c in added
        if sources[c.member_id]["superseded_by"] is not None
    ]
    if problems:
        raise HTTPException(
            409,
            {
                "message": "Some members are a poor fit; pass force to add them anyway.",
                "problems": problems,
            },
        )
