const larkin = require("../larkin");

/* A polygon's references at every level, in the order a client lists them,
   where the database combines them (`map_bounds.polygon_refs_for`); absent, `refs`
   is left out of the response. Expects the polygon aliased as `m`. */
export function refsSelect() {
  if (!larkin.hasCapability("map-refs")) return "";
  return `,
      COALESCE((
        SELECT json_agg(json_build_object(
          'ref_type', r.ref_type, 'label', r.label, 'ref_id', r.ref_id,
          'citation', r.citation, 'doi', r.doi, 'url', r.url
        ) ORDER BY r.ordinality)
        FROM map_bounds.polygon_refs_for(m.map_id) WITH ORDINALITY r
      ), '[]') AS refs`;
}
