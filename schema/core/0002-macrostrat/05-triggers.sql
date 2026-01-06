CREATE TRIGGER lng_lat_insert_trigger BEFORE INSERT OR UPDATE ON macrostrat.cols FOR EACH ROW EXECUTE FUNCTION macrostrat.lng_lat_insert_trigger();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.offshore_baggage FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.offshore_fossils FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_dates FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_dates();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_econs FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_econs();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_environs FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_environs();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_liths FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_liths();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_liths_atts FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_notes FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_notes();

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.units FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_units();

CREATE TRIGGER trg_check_column_project_non_composite BEFORE INSERT OR UPDATE ON macrostrat.cols FOR EACH ROW EXECUTE FUNCTION macrostrat.check_column_project_non_composite();

CREATE TRIGGER trg_check_composite_parent BEFORE INSERT OR UPDATE ON macrostrat.projects_tree FOR EACH ROW EXECUTE FUNCTION macrostrat.check_composite_parent();

