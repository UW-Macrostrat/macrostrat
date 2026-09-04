/* takes care of repeated  note fields*/
WITH a AS(
	SELECT unit_id, GROUP_CONCAT(DISTINCT notes SEPARATOR'; ') as notes from unit_notes group by unit_id 
)
SELECT 
u.id, 
u.strat_name, 
u.color, 
u.outcrop, 
u.FO, 
u.FO_h, 
u.LO, 
u.LO_h, 
u.position_bottom, 
u.position_top, 
u.max_thick, 
u.min_thick, 
u.section_id, 
u.col_id,
a.notes as notes
FROM units u
LEFT JOIN a
ON u.id = a.unit_id
