CREATE TABLE macrostrat.strat_tree_new(
    id serial PRIMARY KEY,
    parent int,
    child int,
    ref_id int
);