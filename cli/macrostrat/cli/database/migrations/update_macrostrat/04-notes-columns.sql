/*
Add notes column to units and column tables
This might be coming from a MariaDB table that isn't preserved?
*/
ALTER TABLE macrostrat.units ADD COLUMN notes text;
ALTER TABLE macrostrat.cols ADD COLUMN notes text;

