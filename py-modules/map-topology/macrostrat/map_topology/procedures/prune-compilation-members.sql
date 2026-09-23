/** Withdraw members that can no longer contribute anything to a compilation.

  A member with no `map_area` row has no boundary, so it holds no territory in
  any layer it reaches: it was ingested and later emptied, or authored into a
  compilation before it had polygons at all.

  This used to be one statement of the layer-membership sweep, where it ran on
  every sync and applied only to served layers. Both were wrong now that
  membership is authored. Deleting an authored edge is a curatorial act, so it
  is a command an operator runs rather than a step that fires behind them; and a
  boundaryless member is exactly as inert in an authored compilation as it is in
  a layer, so there is no reason to treat the two differently.

  Compilations themselves are exempt. A compilation legitimately has no boundary
  until `sync-compilation-bounds` builds one out of its members, so pruning on
  that test would strip a composition on its first sync -- before it could ever
  be assembled. "Is a compilation" is "has members", the same test used
  everywhere else here.
*/
DELETE FROM map_bounds.compilation_member cm
WHERE NOT EXISTS (
  SELECT 1 FROM map_bounds.map_area a WHERE a.source_id = cm.member_id
)
AND NOT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member child
  WHERE child.compilation_id = cm.member_id
);
