
CREATE INDEX ON macrostrat.pbdb_collections_new (collection_no);
CREATE INDEX ON macrostrat.pbdb_collections_new (early_age);
CREATE INDEX ON macrostrat.pbdb_collections_new (late_age);
CREATE INDEX ON macrostrat.pbdb_collections_new USING GiST (geom);

