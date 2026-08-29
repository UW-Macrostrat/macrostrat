/** Suppress no-op UPDATEs on the tables that carry change-tracking triggers.

    suppress_redundant_updates_trigger() is a Postgres built-in: it returns NULL
    when the new row is binary-identical to the old, so no row is written -- no
    dead tuple, and no AFTER trigger, which means no row in audit.record_history
    (see schema/_definitions/audit/).

    This matters because the rebuild scripts recompute derived values across whole
    tables. `unit-boundaries.sql` rewrites all 144,959 rows of unit_boundaries on
    every run to change 29 of them: the recomputed value differs from the stored
    one by a median of 2.5e-05 Ma, which t1_age's numeric(8,4) scale rounds away
    on assignment. Without suppression each run costs ~6 s and ~139 MB of audit
    log; with it, ~0.2 s and ~168 kB, and the resulting table is byte-identical.

    The `a_` prefix is load-bearing. BEFORE triggers fire in name order, and this
    must run ahead of on_update_current_timestamp (which sets date_mod = now(),
    making every row differ). Firing it last suppresses nothing -- measured. A
    genuine change still stamps date_mod as before; a no-op no longer does, which
    is the correct reading of "this row did not change".

    CREATE OR REPLACE (PG14+) so re-applying this file is not an error. **/

CREATE OR REPLACE TRIGGER a_suppress_noop_updates BEFORE UPDATE ON macrostrat.unit_boundaries FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger();

CREATE OR REPLACE TRIGGER a_suppress_noop_updates BEFORE UPDATE ON macrostrat.unit_liths FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger();

CREATE OR REPLACE TRIGGER a_suppress_noop_updates BEFORE UPDATE ON macrostrat.units FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger();

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

