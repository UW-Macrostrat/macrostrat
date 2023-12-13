
/* Assuming there should only be one strat_name per unit */
ALTER TABLE macrostrat.units
	ADD COLUMN strat_name_id int,
	ADD FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;
	
UPDATE macrostrat.units u
SET strat_name_id = sn.strat_name_id 
from macrostrat.unit_strat_names sn 
where u.id = sn.unit_id;