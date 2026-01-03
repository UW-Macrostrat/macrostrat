
create type "macrostrat"."boundary_status" as enum ('', 'modeled', 'relative', 'absolute', 'spike');
create type "macrostrat"."boundary_type" as enum ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');
drop view if exists "macrostrat_api"."unit_boundaries";
drop table "maps_metadata"."sources_metadata";
alter table "macrostrat"."interval_boundaries" alter column "boundary_status" drop default;
alter table "macrostrat"."interval_boundaries_scratch" alter column "boundary_status" drop default;
alter table "macrostrat"."unit_boundaries" alter column "boundary_status" drop default;
alter table "macrostrat"."unit_boundaries" alter column "boundary_type" drop default;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_status" drop default;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_type" drop default;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_status" drop default;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_type" drop default;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_status" drop default;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_type" drop default;
alter table "macrostrat"."interval_boundaries" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."interval_boundaries_scratch" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries" alter column "boundary_type" set data type macrostrat.boundary_type using "boundary_type"::text::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_type" set data type macrostrat.boundary_type using "boundary_type"::text::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_type" set data type macrostrat.boundary_type using "boundary_type"::text::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_status" set data type macrostrat.boundary_status using "boundary_status"::text::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_type" set data type macrostrat.boundary_type using "boundary_type"::text::macrostrat.boundary_type;
alter table "macrostrat"."interval_boundaries" alter column "boundary_status" set default ''::macrostrat.boundary_status;
alter table "macrostrat"."interval_boundaries_scratch" alter column "boundary_status" set default ''::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries" alter column "boundary_status" set default 'modeled'::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries" alter column "boundary_type" set default ''::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_status" set default 'modeled'::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_backup" alter column "boundary_type" set default ''::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_status" set default 'modeled'::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_scratch" alter column "boundary_type" set default ''::macrostrat.boundary_type;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_status" set default 'modeled'::macrostrat.boundary_status;
alter table "macrostrat"."unit_boundaries_scratch_old" alter column "boundary_type" set default ''::macrostrat.boundary_type;
drop type "public"."boundary_status";
drop type "public"."boundary_type";
drop type "macrostrat"."interval_boundaries_boundary_status";
drop type "macrostrat"."interval_boundaries_scratch_boundary_status";
drop type "macrostrat"."unit_boundaries_backup_boundary_status";
drop type "macrostrat"."unit_boundaries_backup_boundary_type";
drop type "macrostrat"."unit_boundaries_boundary_status";
drop type "macrostrat"."unit_boundaries_boundary_type";
drop type "macrostrat"."unit_boundaries_scratch_boundary_status";
drop type "macrostrat"."unit_boundaries_scratch_boundary_type";
drop type "macrostrat"."unit_boundaries_scratch_old_boundary_status";
drop type "macrostrat"."unit_boundaries_scratch_old_boundary_type";
create or replace view "macrostrat_api"."unit_boundaries" as  SELECT unit_boundaries.id,
    unit_boundaries.t1,
    unit_boundaries.t1_prop,
    unit_boundaries.t1_age,
    unit_boundaries.unit_id,
    unit_boundaries.unit_id_2,
    unit_boundaries.section_id,
    unit_boundaries.boundary_position,
    unit_boundaries.boundary_type,
    unit_boundaries.boundary_status,
    unit_boundaries.paleo_lat,
    unit_boundaries.paleo_lng,
    unit_boundaries.ref_id
   FROM macrostrat.unit_boundaries;
