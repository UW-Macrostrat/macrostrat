insert into maps.point_type (point_type)
select distinct point_type
from maps.points
where point_type is not null;

insert into maps.line_type (line_type)
select distinct type
from maps.lines
where type is not null;
