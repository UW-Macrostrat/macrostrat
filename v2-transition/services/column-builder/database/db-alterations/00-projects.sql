CREATE TABLE IF NOT EXISTS macrostrat.projects(
    id SERIAL PRIMARY KEY,
    project text,
    descrip text,
    timescale_id integer REFERENCES macrostrat.timescales(id)
);

INSERT INTO "macrostrat"."projects"("id","project","descrip","timescale_id")
VALUES
(1,E'North America',E'Composite column dataset for the USA and Canada.',1),
(3,E'eODP',E'Comprehensive dataset capturing all offshore drilling sites and holes. Holes at each site are captured as \'section\' column types and meters below sea floor (mbsf) are encoded by \'t_pos\' and \'b_pos\' when \'show_position\' parameter is included. Project led by Andy Fraass, Leah LeVay, Jocelyn Sessa, and Shanan Peters.',1),
(4,E'Deep Sea',E'Offshore drilling sites completely cored from sea floor into or near basement rocks. Most sites in this compilation are composited manually from multiple holes into a single representation for the site. Data compiled from offshore drilling reports by S.E. Peters, D.C. Kelly, and A.Fraass. See project_id=3 (\'eODP\') for complete offshore drilling data and associated measurements.',5),
(5,E'New Zealand',E'Primarily measured section-type columns for Late Cretaceous to Recent.',6),
(6,E'Australia',E'Placeholder for anticipated column entry work.',1),
(7,E'Caribbean',E'Composite column dataset for the Caribbean region, including the eastern Gulf Coast of Mexico and Central America.',1),
(8,E'South America',E'Composite column dataset for South America.',1),
(9,E'Africa',E'Composite column dataset for Africa.',1),
(10,E'North American Ediacaran',E'Composite columns of intermediate scale resolution that are comprehensive for the Ediacaran System of present-day North America and adjacent continental blocks formerly part of North America. Compiled by D. Segessenman as part of his Ph.D.',1),
(11,E'North American Cretaceous',E'Cretaceous-focused intermediate scale resolution section data set compiled by Shan Ye as part of his Ph.D.',1),
(12,E'Indonesia',E'Composite column dataset for Indonesia. Compiled principally by Afiqah Ahmad Rafi as part of her senior thesis at UW-Madison.',1);