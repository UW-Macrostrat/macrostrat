-- If we already have types in place, we need to rename them first
alter type "macrostrat"."measurement_class" rename to "measurement_class_temp";
alter type "macrostrat"."measurement_type" rename to "measurement_type_temp";

alter type "public"."measurement_class" set schema macrostrat;
alter type "public"."measurement_type" set schema macrostrat;

alter table "macrostrat"."lookup_measurements" alter column "measurement_class" set data type macrostrat.measurement_class using "measurement_class"::text::macrostrat.measurement_class;
alter table "macrostrat"."lookup_measurements" alter column "measurement_type" set data type macrostrat.measurement_type using "measurement_type"::text::macrostrat.measurement_type;
alter table "macrostrat"."measurements" alter column "measurement_class" set data type macrostrat.measurement_class using "measurement_class"::text::macrostrat.measurement_class;
alter table "macrostrat"."measurements" alter column "measurement_type" set data type macrostrat.measurement_type using "measurement_type"::text::macrostrat.measurement_type;
drop type "macrostrat"."lookup_measurements_measurement_class";
drop type "macrostrat"."lookup_measurements_measurement_type";
drop type "macrostrat"."measurements_measurement_class";
drop type "macrostrat"."measurements_measurement_type";
drop type "macrostrat"."measurement_class_temp";
drop type "macrostrat"."measurement_type_temp";
drop type "public"."measurement_class_new";
drop type "public"."measurement_type_new";
