
CREATE TABLE macrostrat.strat_names_meta_new (
    concept_id integer PRIMARY KEY,
    orig_id integer NOT NULL,
    name character varying(40),
    geologic_age text,
    interval_id integer NOT NULL,
    b_int integer NOT NULL,
    t_int integer NOT NULL,
    usage_notes text,
    other text,
    province text,
    url character varying(150),
    ref_id integer NOT NULL
);

