/* 
recursive query, gets all the children of a strat_name, this time by id = 102247
creates a text path representing the hierarchy of strat_names
 */
with recursive children as (
	select 
		parent, child, st.ref_id, 
        CAST(concat(CAST(sn.strat_name as text), '.', CAST(snt.strat_name as text)) as text) as path
	from 
		macrostrat.strat_tree st
	join macrostrat.strat_names sn
	on st.parent = sn.id
	join macrostrat.strat_names snt
	on st.child = snt.id	 
	where 
		parent = 102247
	union
		select 
			t.parent, t.child, t.ref_id, 
            CAST(concat(c.path, '.',snn.strat_name) as text) as path
		from
			macrostrat.strat_tree t
		join macrostrat.strat_names snn
		on t.child = snn.id	
		inner join children c 
		on c.child = t.parent	
) select c.*, snn.strat_name parent, sn.strat_name child from children c
left join macrostrat.strat_names sn
on sn.id = c.child
left join macrostrat.strat_names snn
on snn.id = c.parent;

/* 
Similar to above but instead creates a jsonb[] of the strat_name records that represent
the hierarchy 
 */
with recursive children as (
	select 
		parent, child, st.ref_id, 
        '[]' || to_jsonb(sn.*) || to_jsonb(snt.*) as path
	from 
		macrostrat.strat_tree st
	join macrostrat.strat_names sn
	on st.parent = sn.id
	join macrostrat.strat_names snt
	on st.child = snt.id	 
	where 
		parent = 102247
	union
		select 
			t.parent, t.child, t.ref_id, 
            c.path || to_jsonb(snn.*) as path
		from
			macrostrat.strat_tree t
		join macrostrat.strat_names snn
		on t.child = snn.id	
		inner join children c 
		on c.child = t.parent	
) select c.*, snn.strat_name parent, sn.strat_name child from children c
left join macrostrat.strat_names sn
on sn.id = c.child
left join macrostrat.strat_names snn
on snn.id = c.parent;