
CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);
ALTER TABLE hexgrids.bedrock_index OWNER TO macrostrat;

CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);
ALTER TABLE hexgrids.hexgrids OWNER TO macrostrat;

CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);

ALTER TABLE hexgrids.pbdb_index OWNER TO macrostrat;

CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r10 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE hexgrids.r10_ogc_fid_seq OWNER TO macrostrat;
ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;
CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);
ALTER TABLE hexgrids.r11 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r11_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;

CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r12 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r12_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;

CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r5 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r5_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;

CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r6 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r6_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;

CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r7 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r7_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;

CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r8 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r8_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;

CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

ALTER TABLE hexgrids.r9 OWNER TO macrostrat;

CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE hexgrids.r9_ogc_fid_seq OWNER TO macrostrat;

ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;

ALTER TABLE ONLY hexgrids.r10 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r10_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r11 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r11_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r12 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r12_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r5 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r5_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r6 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r6_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r7 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r7_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r8 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r8_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r9 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r9_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.hexgrids
    ADD CONSTRAINT hexgrids_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r10
    ADD CONSTRAINT r10_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r11
    ADD CONSTRAINT r11_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r12
    ADD CONSTRAINT r12_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r5
    ADD CONSTRAINT r5_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r6
    ADD CONSTRAINT r6_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r7
    ADD CONSTRAINT r7_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r8
    ADD CONSTRAINT r8_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r9
    ADD CONSTRAINT r9_pkey PRIMARY KEY (hex_id);

CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);

CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);

CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);

CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);

CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);

CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);

CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);

CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);

CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);
CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);
CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);
CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);
CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);
CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);
CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);
CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);
CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);
CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);
CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);
CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);
CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);
CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);
CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);
CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);
CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);
CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);
CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);
CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);
CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);
CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA hexgrids GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA hexgrids GRANT SELECT ON TABLES  TO macrostrat;

