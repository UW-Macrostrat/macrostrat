CREATE TABLE macrostrat.projects (
    id serial PRIMARY KEY,
    project text,
    descrip text,
    timescale_id int,
    FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id)
);

INSERT INTO macrostrat.projects (id, project, descrip, timescale_id)
VALUES
	(1, 'North America', 'Composite column dataset for the USA and Canada.', 1),
	(4, 'Deep Sea', 'Offshore drilling sites completely cored from sea floor into or near basement rocks. Most sites in this compilation are composited manually from multiple holes into a single representation for the site. Data compiled from offshore drilling reports by S.E. Peters, D.C. Kelly, and A.Fraass. See project_id=3 (''eODP'') for complete offshore drilling data and associated measurements.', 5),
	(5, 'New Zealand', 'Primarily measured section-type columns for Late Cretaceous to Recent.', 6),
	(6, 'Australia', 'Placeholder for anticipated column entry work.', 1),
	(7, 'Caribbean', 'Composite column dataset for the Caribbean region, including the eastern Gulf Coast of Mexico and Central America.', 1),
	(8, 'South America', 'Composite column dataset for South America.', 1),
	(9, 'Africa', 'Composite column dataset for Africa.', 1),
	(10, 'North American Ediacaran', 'Composite columns of intermediate scale resolution that are comprehensive for the Ediacaran System of present-day North America and adjacent continental blocks formerly part of North America. Compiled by D. Segessenman as part of his Ph.D.', 1),
	(11, 'North American Cretaceous', 'Cretaceous-focused intermediate scale resolution section data set compiled by Shan Ye as part of his Ph.D.', 1),
	(12, 'Indonesia', 'Composite column dataset for Indonesia. Compiled principally by Afiqah Ahmad Rafi as part of her senior thesis at UW-Madison.', 1),
	(3, 'eODP', 'Comprehensive dataset capturing all offshore drilling sites and holes. Holes at each site are captured as ''section'' column types and meters below sea floor (mbsf) are encoded by ''t_pos'' and ''b_pos'' when ''show_position'' parameter is included. Project led by Andy Fraass, Leah LeVay, Jocelyn Sessa, and Shanan Peters.', 1);
