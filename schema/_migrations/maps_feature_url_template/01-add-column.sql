ALTER TABLE maps.sources ADD COLUMN feature_url_template text
  CONSTRAINT sources_feature_url_template_has_orig_id
  CHECK (strpos(feature_url_template, '{orig_id}') > 0);
