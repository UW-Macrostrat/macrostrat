/* Which carto build answers a map query that names no `source`.

   `CARTO_BUILD` is shared with both tileservers, so one setting per environment
   decides the tiles and the point queries together: `compilation` answers from
   `carto`, `legacy` (the default) from the materialized `carto.*` build. */

// The materialized `carto.*` build, addressed like a source; never a
// `maps.sources` row, so it has no zoom range of its own.
export const LEGACY_CARTO = "sys:carto-legacy";

export function cartoFromCompilation(env = process.env): boolean {
  return env.CARTO_BUILD?.trim().toLowerCase() == "compilation";
}

/** The `source` a request asks for, or the environment's default: `carto`, or
 * null for the legacy query, which runs unchanged. */
export function requestedSource(query, env = process.env): string | null {
  // `compilation` is the earlier name, accepted until clients have moved.
  const param = query.source ?? query.compilation;
  if (param) return String(param);
  if (cartoFromCompilation(env)) return "carto";
  return null;
}
