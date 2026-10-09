-- PostgREST routes for saved locations

CREATE VIEW macrostrat_api.location_tags AS
 SELECT location_tags.id,
    location_tags.name,
    location_tags.description,
    location_tags.color
   FROM user_features.location_tags;

-- security_invoker so the base table's row security applies to the caller
-- rather than to the view's owner, who bypasses it.
CREATE VIEW macrostrat_api.location_tags_intersect WITH (security_invoker='true') AS
 SELECT location_tags_intersect.tag_id,
    location_tags_intersect.user_id,
    location_tags_intersect.location_id
   FROM user_features.location_tags_intersect;

CREATE VIEW macrostrat_api.user_locations_view WITH (security_invoker='true') AS
 SELECT user_locations.id,
    user_locations.user_id,
    user_locations.name,
    user_locations.description,
    user_locations.point,
    user_locations.zoom,
    user_locations.meters_from_point,
    user_locations.elevation,
    user_locations.azimuth,
    user_locations.pitch,
    user_locations.map_layers
   FROM user_features.user_locations;

GRANT SELECT ON TABLE macrostrat_api.location_tags TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.location_tags TO web_user;

GRANT SELECT ON TABLE macrostrat_api.location_tags TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.location_tags_intersect TO web_anon;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_api.location_tags_intersect TO web_user;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_api.location_tags_intersect TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.user_locations_view TO web_anon;

GRANT SELECT,DELETE ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT SELECT,DELETE ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT UPDATE(id) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT UPDATE(id) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(user_id),UPDATE(user_id) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(user_id),UPDATE(user_id) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(name),UPDATE(name) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(name),UPDATE(name) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(description),UPDATE(description) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(description),UPDATE(description) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(point),UPDATE(point) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(point),UPDATE(point) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(zoom),UPDATE(zoom) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(zoom),UPDATE(zoom) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(meters_from_point),UPDATE(meters_from_point) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(meters_from_point),UPDATE(meters_from_point) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(elevation),UPDATE(elevation) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(elevation),UPDATE(elevation) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(azimuth),UPDATE(azimuth) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(azimuth),UPDATE(azimuth) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(pitch),UPDATE(pitch) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(pitch),UPDATE(pitch) ON TABLE macrostrat_api.user_locations_view TO web_admin;

GRANT INSERT(map_layers),UPDATE(map_layers) ON TABLE macrostrat_api.user_locations_view TO web_user;

GRANT INSERT(map_layers),UPDATE(map_layers) ON TABLE macrostrat_api.user_locations_view TO web_admin;
