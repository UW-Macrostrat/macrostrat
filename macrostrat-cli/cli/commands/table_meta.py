from collections import OrderedDict
tables = OrderedDict({
    # "": {
    #     "dump": """
    #
    #     """,
    #     "create": """
    #
    #     """,
    #     "insert": """
    #
    #     """,
    #     "index": """
    #
    #     """,
    #     "process": """
    #
    #     """
    # },

    "unit_strat_names": {
        "dump": """
            SELECT id, unit_id, strat_name_id
            FROM unit_strat_names
        """,
        "create": """
            CREATE TABLE macrostrat.unit_strat_names_new (
              id serial PRIMARY KEY NOT NULL,
              unit_id integer NOT NULL,
              strat_name_id integer NOT NULL
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_strat_names_new (id, unit_id, strat_name_id) VALUES (%(id)s, %(unit_id)s, %(strat_name_id)s);
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_strat_names_new (unit_id);
            CREATE INDEX ON macrostrat.unit_strat_names_new (strat_name_id);
        """,
        "process": """ """,
        "finish": """
            COMMENT ON TABLE macrostrat.unit_strat_names_new IS %s;
            ALTER TABLE macrostrat.unit_strat_names RENAME TO unit_strat_names_old;
            ALTER TABLE macrostrat.unit_strat_names_new RENAME TO unit_strat_names;
            DROP TABLE macrostrat.unit_strat_names_old;
        """
    },

    "strat_names": {
        "dump": """
            SELECT id, strat_name, rank, ref_id, concept_id
            FROM strat_names
        """,
        "create": """
            CREATE TABLE macrostrat.strat_names_new (
              id serial PRIMARY KEY NOT NULL,
              strat_name character varying(100) NOT NULL,
              rank character varying(50),
              ref_id  integer NOT NULL,
              concept_id integer
            )
        """,
        "insert": """
            INSERT INTO macrostrat.strat_names_new (id, strat_name, rank, ref_id, concept_id) VALUES (%(id)s, %(strat_name)s, %(rank)s, %(ref_id)s, %(concept_id)s);
        """,
        "index": """
            CREATE INDEX ON macrostrat.strat_names_new (strat_name);
            CREATE INDEX ON macrostrat.strat_names_new (rank);
            CREATE INDEX ON macrostrat.strat_names_new (ref_id);
            CREATE INDEX ON macrostrat.strat_names_new (concept_id);
        """,
        "process": """

        """
    },

    "units_sections": {
        "dump": """
            SELECT id, unit_id, section_id, col_id
            FROM units_sections
        """,
        "create": """
            CREATE TABLE macrostrat.units_sections_new (
              id serial PRIMARY KEY NOT NULL,
              unit_id integer NOT NULL,
              section_id integer NOT NULL,
              col_id integer NOT NULL
            );
        """,
        "insert": """
            INSERT INTO macrostrat.units_sections_new (id, unit_id, section_id, col_id) VALUES (%(id)s, %(unit_id)s, %(section_id)s, %(col_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.units_sections_new (unit_id);
            CREATE INDEX ON macrostrat.units_sections_new (section_id);
            CREATE INDEX ON macrostrat.units_sections_new (col_id);
        """,
        "process": """

        """
    },

    "intervals": {
        "dump": """
            SELECT id, age_bottom, age_top, interval_name, interval_abbrev, interval_type, interval_color
            FROM intervals
        """,
        "create": """
            CREATE TABLE macrostrat.intervals_new (
              id serial NOT NULL,
              age_bottom numeric,
              age_top numeric,
              interval_name character varying(200),
              interval_abbrev character varying(50),
              interval_type character varying(50),
              interval_color character varying(20),
              rank integer DEFAULT NULL
            );
        """,
        "insert": """
            INSERT INTO macrostrat.intervals_new (id, age_bottom, age_top, interval_name, interval_abbrev, interval_type, interval_color) VALUES (%(id)s, %(age_bottom)s, %(age_top)s, %(interval_name)s, %(interval_abbrev)s, %(interval_type)s, %(interval_color)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.intervals_new (id);
            CREATE INDEX ON macrostrat.intervals_new (age_top);
            CREATE INDEX ON macrostrat.intervals_new (age_bottom);
            CREATE INDEX ON macrostrat.intervals_new (interval_type);
            CREATE INDEX ON macrostrat.intervals_new (interval_name);
        """,
        "process": """
            INSERT INTO macrostrat.intervals_new (id, interval_name, interval_color) VALUES (0, 'Unknown', '#737373');

            UPDATE macrostrat.intervals_new SET rank = 6 WHERE interval_type = 'age';
            UPDATE macrostrat.intervals_new SET rank = 5 WHERE interval_type = 'epoch';
            UPDATE macrostrat.intervals_new SET rank = 4 WHERE interval_type = 'period';
            UPDATE macrostrat.intervals_new SET rank = 3 WHERE interval_type = 'era';
            UPDATE macrostrat.intervals_new SET rank = 2 WHERE interval_type = 'eon';
            UPDATE macrostrat.intervals_new SET rank = 1 WHERE interval_type = 'supereon';
            UPDATE macrostrat.intervals_new SET rank = 0 WHERE rank IS NULL;
        """
    },

    "lookup_unit_intervals": {
        "dump": """
            SELECT unit_id, fo_age, b_age, fo_interval, fo_period, lo_age, t_age, lo_interval, lo_period, age, age_id, epoch, epoch_id, period, period_id, era, era_id, eon, eon_id
            FROM lookup_unit_intervals
        """,
        "create": """
            CREATE TABLE macrostrat.lookup_unit_intervals_new (
              unit_id integer,
              FO_age numeric,
              b_age numeric,
              FO_interval character varying(50),
              FO_period character varying(50),
              LO_age numeric,
              t_age numeric,
              LO_interval character varying(50),
              LO_period character varying(50),
              age character varying(50),
              age_id integer,
              epoch character varying(50),
              epoch_id integer,
              period character varying(50),
              period_id integer,
              era character varying(50),
              era_id integer,
              eon character varying(50),
              eon_id integer,
              best_interval_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lookup_unit_intervals_new (unit_id, FO_age, b_age, FO_interval, FO_period, LO_age, t_age, LO_interval, LO_period, age, age_id, epoch, epoch_id, period, period_id, era, era_id, eon, eon_id) VALUES (%(unit_id)s, %(fo_age)s, %(b_age)s, %(fo_interval)s, %(fo_period)s, %(lo_age)s, %(t_age)s, %(lo_interval)s, %(lo_period)s, %(age)s, %(age_id)s, %(epoch)s, %(epoch_id)s, %(period)s, %(period_id)s, %(era)s, %(era_id)s, %(eon)s, %(eon_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lookup_unit_intervals_new (unit_id);
            CREATE INDEX ON macrostrat.lookup_unit_intervals_new (best_interval_id);
        """,
        "process": """
            WITH bests AS (
              select unit_id,
                CASE
                  WHEN age_id > 0 THEN
                    age_id
                  WHEN epoch_id > 0 THEN
                    epoch_id
                  WHEN period_id > 0 THEN
                    period_id
                  WHEN era_id > 0 THEN
                    era_id
                  WHEN eon_id > 0 THEN
                    eon_id
                  ELSE
                    0
                END
               AS b_interval_id from macrostrat.lookup_unit_intervals_new
            )
            UPDATE macrostrat.lookup_unit_intervals_new lui
            SET best_interval_id = b_interval_id
            FROM bests
            WHERE lui.unit_id = bests.unit_id;
        """
    },

    "units": {
        "dump": """
            SELECT id, strat_name, color, outcrop, FO, FO_h, LO, LO_h, position_bottom, position_top, max_thick, min_thick, section_id, col_id
            FROM units
        """,
        "create": """
            CREATE TABLE macrostrat.units_new (
              id integer PRIMARY KEY,
              strat_name character varying(150),
              color character varying(20),
              outcrop character varying(20),
              FO integer,
              FO_h integer,
              LO integer,
              LO_h integer,
              position_bottom numeric,
              position_top numeric,
              max_thick numeric,
              min_thick numeric,
              section_id integer,
              col_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.units_new (id, strat_name, color, outcrop, FO, FO_h, LO, LO_h, position_bottom, position_top, max_thick, min_thick, section_id, col_id) VALUES (%(id)s, %(strat_name)s, %(color)s, %(outcrop)s, %(FO)s, %(FO_h)s, %(LO)s, %(LO_h)s, %(position_bottom)s, %(position_top)s, %(max_thick)s, %(min_thick)s, %(section_id)s, %(col_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.units_new (section_id);
            CREATE INDEX ON macrostrat.units_new (col_id);
            CREATE INDEX ON macrostrat.units_new (strat_name);
            CREATE INDEX ON macrostrat.units_new (color);
        """,
        "process": """

        """
    },

    "lookup_strat_names": {
        "dump": """
            SELECT strat_name_id, strat_name, rank, concept_id, rank_name, bed_id, bed_name, mbr_id, mbr_name, fm_id, fm_name, gp_id, gp_name, sgp_id, sgp_name, early_age, late_age, gsc_lexicon, b_period, t_period, c_interval, name_no_lith
            FROM lookup_strat_names
        """,
        "create": """
            CREATE TABLE macrostrat.lookup_strat_names_new (
              strat_name_id integer,
              strat_name character varying(100),
              rank character varying(20),
              concept_id integer,
              rank_name character varying(200),
              bed_id integer,
              bed_name character varying(100),
              mbr_id integer,
              mbr_name character varying(100),
              fm_id integer,
              fm_name character varying(100),
              gp_id integer,
              gp_name character varying(100),
              sgp_id integer,
              sgp_name character varying(100),
              early_age numeric,
              late_age numeric,
              gsc_lexicon character varying(20),
              b_period character varying(100),
              t_period character varying(100),
              c_interval character varying(100),
              name_no_lith character varying(100)
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lookup_strat_names_new (strat_name_id, strat_name, rank, concept_id, rank_name, bed_id, bed_name, mbr_id, mbr_name, fm_id, fm_name, gp_id, gp_name, sgp_id, sgp_name, early_age, late_age, gsc_lexicon, b_period, t_period, c_interval, name_no_lith) VALUES (%(strat_name_id)s, %(strat_name)s, %(rank)s, %(concept_id)s, %(rank_name)s, %(bed_id)s, %(bed_name)s, %(mbr_id)s, %(mbr_name)s, %(fm_id)s, %(fm_name)s, %(gp_id)s, %(gp_name)s, %(sgp_id)s, %(sgp_name)s, %(early_age)s, %(late_age)s, %(gsc_lexicon)s, %(b_period)s, %(t_period)s, %(c_interval)s, %(name_no_lith)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lookup_strat_names_new (strat_name_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (concept_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (bed_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (mbr_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (fm_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (gp_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (sgp_id);
            CREATE INDEX ON macrostrat.lookup_strat_names_new (strat_name);
        """,
        "process": """

        """
    },

    "col_areas": {
        "dump": """
            SELECT id, col_id, null as col_area, ST_AsText(col_area) AS wkt
            FROM col_areas
        """,
        "create": """
            CREATE TABLE macrostrat.col_areas_new (
              id integer PRIMARY KEY,
              col_id integer,
              col_area geometry,
              wkt text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.col_areas_new (id, col_id, col_area, wkt) VALUES (%(id)s, %(col_id)s, %(col_area)s, %(wkt)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.col_areas_new (col_id);
            CREATE INDEX ON macrostrat.col_areas_new USING GIST (col_area);
        """,
        "process": """
            UPDATE macrostrat.col_areas_new SET col_area = ST_GeomFromText(wkt);
        """
    },

    "cols": {
        "dump": """
            SELECT id, col_group_id, project_id, status_code, col_position, col, col_name, lat, lng, col_area, ST_AsText(coordinate) AS wkt, created
            FROM cols
        """,
        "create": """
            CREATE TABLE macrostrat.cols_new (
              id integer PRIMARY KEY,
              col_group_id smallint,
              project_id smallint,
              status_code character varying(25),
              col_position character varying(25),
              col numeric,
              col_name character varying(100),
              lat numeric,
              lng numeric,
              col_area numeric,
              coordinate geometry,
              wkt text,
              created text,
              poly_geom geometry
            );
        """,
        "insert": """
            INSERT INTO macrostrat.cols_new (id, col_group_id, project_id, status_code, col_position, col, col_name, lat, lng, col_area, wkt, created) VALUES (%(id)s, %(col_group_id)s, %(project_id)s, %(status_code)s, %(col_position)s, %(col)s, %(col_name)s, %(lat)s, %(lng)s, %(col_area)s, %(wkt)s, %(created)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.cols_new (project_id);
            CREATE INDEX ON macrostrat.cols_new USING GIST (coordinate);
            CREATE INDEX ON macrostrat.cols_new USING GIST (poly_geom);
            CREATE INDEX ON macrostrat.cols_new (col_group_id);
            CREATE INDEX ON macrostrat.cols_new (status_code);
        """,
        "process": """
            UPDATE macrostrat.cols_new AS c
            SET poly_geom = a.col_area
            FROM macrostrat.col_areas a
            WHERE c.id = a.col_id;

            UPDATE macrostrat.cols_new SET coordinate = ST_GeomFromText(wkt);
            UPDATE macrostrat.cols_new SET poly_geom = ST_SetSRID(poly_geom, 4326);
        """
    },

    "liths": {
        "dump": """
            SELECT id, lith, lith_group, lith_type, lith_class, lith_equiv, lith_fill, comp_coef, initial_porosity, bulk_density, lith_color
            FROM liths
        """,
        "create": """
            CREATE TABLE macrostrat.liths_new (
              id integer PRIMARY KEY NOT NULL,
              lith character varying(75),
              lith_group text,
              lith_type character varying(50),
              lith_class character varying(50),
              lith_equiv integer,
              lith_fill integer,
              comp_coef numeric,
              initial_porosity numeric,
              bulk_density numeric,
              lith_color character varying(12)
            );
        """,
        "insert": """
            INSERT INTO macrostrat.liths_new ( id, lith, lith_group, lith_type, lith_class, lith_equiv, lith_fill, comp_coef, initial_porosity, bulk_density, lith_color) VALUES (%(id)s, %(lith)s, %(lith_group)s, %(lith_type)s, %(lith_class)s, %(lith_equiv)s, %(lith_fill)s, %(comp_coef)s, %(initial_porosity)s, %(bulk_density)s, %(lith_color)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.liths_new (lith);
            CREATE INDEX ON macrostrat.liths_new (lith_class);
            CREATE INDEX ON macrostrat.liths_new (lith_type);
        """,
        "process": """

        """
    },

    "lith_atts": {
        "dump": """
            SELECT id, lith_att, att_type, lith_att_fill
            FROM lith_atts
        """,
        "create": """
            CREATE TABLE macrostrat.lith_atts_new (
              id integer PRIMARY KEY NOT NULL,
              lith_att character varying(75),
              att_type character varying(25),
              lith_att_fill integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lith_atts_new (id, lith_att, att_type, lith_att_fill) VALUES (%(id)s, %(lith_att)s, %(att_type)s, %(lith_att_fill)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lith_atts_new (att_type);
            CREATE INDEX ON macrostrat.lith_atts_new (lith_att);
        """,
        "process": """

        """
    },

    "timescales_intervals": {
        "dump": """
            SELECT timescale_id, interval_id
            FROM timescales_intervals
        """,
        "create": """
            CREATE TABLE macrostrat.timescales_intervals_new (
              timescale_id integer,
              interval_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.timescales_intervals_new (timescale_id, interval_id) VALUES (%(timescale_id)s, %(interval_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.timescales_intervals_new (timescale_id);
            CREATE INDEX ON macrostrat.timescales_intervals_new (interval_id);
        """,
        "process": """

        """
    },

    "unit_liths": {
        "dump": """
              SELECT id, lith_id, unit_id, prop, dom, comp_prop, mod_prop, toc, ref_id
              FROM unit_liths
        """,
        "create": """
            CREATE TABLE macrostrat.unit_liths_new (
              id integer PRIMARY KEY,
              lith_id integer,
              unit_id integer,
              prop text,
              dom character varying(10),
              comp_prop numeric,
              mod_prop numeric,
              toc numeric,
              ref_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_liths_new (id, lith_id, unit_id, prop, dom, comp_prop, mod_prop, toc, ref_id) VALUES (%(id)s, %(lith_id)s, %(unit_id)s, %(prop)s, %(dom)s, %(comp_prop)s, %(mod_prop)s, %(toc)s, %(ref_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_liths_new (unit_id);
            CREATE INDEX ON macrostrat.unit_liths_new (lith_id);
            CREATE INDEX ON macrostrat.unit_liths_new (ref_id);
        """,
        "process": """

        """
    },

    "lookup_unit_liths": {
        "dump": """
            SELECT unit_id, lith_class, lith_type, lith_short, lith_long, environ_class, environ_type, environ
            FROM lookup_unit_liths
        """,
        "create": """
            CREATE TABLE macrostrat.lookup_unit_liths_new (
              unit_id integer,
              lith_class character varying(100),
              lith_type character varying(100),
              lith_short text,
              lith_long text,
              environ_class character varying(100),
              environ_type character varying(100),
              environ character varying(255)
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lookup_unit_liths_new (unit_id, lith_class, lith_type, lith_short, lith_long, environ_class, environ_type, environ) VALUES (%(unit_id)s, %(lith_class)s, %(lith_type)s, %(lith_short)s, %(lith_long)s, %(environ_class)s, %(environ_type)s, %(environ)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lookup_unit_liths_new (unit_id);
        """,
        "process": """

        """
    },

    "timescales": {
        "dump": """
            SELECT id, timescale, ref_id
            FROM timescales
        """,
        "create": """
            CREATE TABLE macrostrat.timescales_new (
              id integer PRIMARY KEY,
              timescale character varying(100),
              ref_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.timescales_new (id, timescale, ref_id) VALUES (%(id)s, %(timescale)s, %(ref_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.timescales_new (timescale);
            CREATE INDEX ON macrostrat.timescales_new (ref_id);
        """,
        "process": """

        """
    },

    "col_groups": {
        "dump": """
             SELECT id, col_group, col_group_long
             FROM col_groups
        """,
        "create": """
            CREATE TABLE macrostrat.col_groups_new (
                id integer PRIMARY KEY,
                col_group character varying(100),
                col_group_long character varying(100)
            );
        """,
        "insert": """
            INSERT INTO macrostrat.col_groups_new (id, col_group, col_group_long ) VALUES (%(id)s, %(col_group)s, %(col_group_long)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.col_groups_new (id);
        """,
        "process": """

        """
    },

    "col_refs": {
        "dump": """
            SELECT id, col_id, ref_id
            FROM col_refs
        """,
        "create": """
            CREATE TABLE macrostrat.col_refs_new (
                id integer PRIMARY KEY,
                col_id integer,
                ref_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.col_refs_new (id, col_id, ref_id) VALUES (%(id)s, %(col_id)s, %(ref_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.col_refs_new (col_id);
            CREATE INDEX ON macrostrat.col_refs_new (ref_id);
        """,
        "process": """

        """
    },

    "strat_names_meta": {
        "dump": """
            SELECT concept_id, orig_id, name, geologic_age, interval_id, b_int, t_int, usage_notes, other, province, url, ref_id
            FROM strat_names_meta
        """,
        "create": """
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
        """,
        "insert": """
            INSERT INTO macrostrat.strat_names_meta_new (concept_id, orig_id, name, geologic_age, interval_id, b_int, t_int, usage_notes, other, province, url, ref_id) VALUES (%(concept_id)s, %(orig_id)s, %(name)s, %(geologic_age)s, %(interval_id)s, %(b_int)s, %(t_int)s, %(usage_notes)s, %(other)s, %(province)s, %(url)s, %(ref_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.strat_names_meta_new (interval_id);
            CREATE INDEX ON macrostrat.strat_names_meta_new (b_int);
            CREATE INDEX ON macrostrat.strat_names_meta_new (t_int);
            CREATE INDEX ON macrostrat.strat_names_meta_new (ref_id);
        """,
        "process": """

        """
    },

    "refs": {
        "dump": """
            SELECT id, pub_year, author, ref, doi, compilation_code, url, ST_AsText(rgeom) rgeom
            FROM refs
        """,
        "create": """
            CREATE TABLE macrostrat.refs_new (
                id integer PRIMARY key,
                pub_year integer,
                author character varying(255),
                ref text,
                doi character varying(40),
                compilation_code character varying(100),
                url text,
                rgeom geometry
            );
        """,
        "insert": """
            INSERT INTO macrostrat.refs_new (id, pub_year, author, ref, doi, compilation_code, url, rgeom) VALUES (%(id)s, %(pub_year)s, %(author)s, %(ref)s, %(doi)s, %(compilation_code)s, %(url)s, ST_SetSRID(ST_GeomFromText(%(rgeom)s), 4326))
        """,
        "index": """
            CREATE INDEX ON macrostrat.refs_new USING GiST (rgeom);
        """,
        "process": """

        """
    },

    "places": {
        "dump": """
            SELECT place_id, name, abbrev, postal, country, country_abbrev, ST_AsText(geom) geom
            FROM places
        """,
        "create": """
            CREATE TABLE macrostrat.places_new (
                place_id integer PRIMARY KEY,
                name text,
                abbrev text,
                postal text,
                country text,
                country_abbrev text,
                geom geometry
            );
        """,
        "insert": """
            INSERT INTO macrostrat.places_new (place_id, name, abbrev, postal, country, country_abbrev, geom) VALUES (%(place_id)s, %(name)s, %(abbrev)s, %(postal)s, %(country)s, %(country_abbrev)s, ST_SetSRID(ST_GeomFromText(%(geom)s), 4326))
        """,
        "index": """
            CREATE INDEX ON macrostrat.places_new USING GiST (geom);
        """,
        "process": """

        """
    },

    "strat_names_places": {
        "dump": """
            SELECT strat_name_id, place_id
            FROM strat_names_places
        """,
        "create": """
            CREATE TABLE macrostrat.strat_names_places_new (
                strat_name_id integer NOT NULL,
                place_id integer NOT NULL
            );
        """,
        "insert": """
            INSERT INTO macrostrat.strat_names_places (strat_name_id, place_id) VALUES (%(strat_name_id)s, %(place_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.strat_names_places_new (strat_name_id);
            CREATE INDEX ON macrostrat.strat_names_places_new (place_id);
        """,
        "process": """

        """
    },

    "concepts_places": {
        "dump": """
            SELECT concept_id, place_id
            FROM concepts_places
        """,
        "create": """
            CREATE TABLE macrostrat.concepts_places_new (
                concept_id integer NOT NULL,
                place_id integer NOT NULL
            );
        """,
        "insert": """
            INSERT INTO macrostrat.concepts_places_new (concept_id, place_id) VALUES (%(concept_id)s, %(place_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.concepts_places_new (concept_id);
            CREATE INDEX ON macrostrat.concepts_places_new (place_id);
        """,
        "process": """

        """
    },

    "lookup_units": {
        "dump": """
            SELECT unit_id, col_area, project_id, t_int, t_int_name, t_int_age, t_age, t_prop, t_plat, t_plng, b_int, b_int_name, b_int_age, b_age, b_prop, b_plat, b_plng, clat, clng, color, text_color, units_above, units_below, pbdb_collections, pbdb_occurrences, age, age_id, epoch, epoch_id, period, period_id, era, era_id, eon, eon_id
            FROM lookup_units
        """,
        "create": """
            CREATE TABLE macrostrat.lookup_units_new (
              unit_id integer PRIMARY KEY NOT NULL,
              col_area numeric NOT NULL,
              project_id integer NOT NULL,
              t_int integer,
              t_int_name text,
              t_int_age numeric,
              t_age numeric,
              t_prop numeric,
              t_plat numeric,
              t_plng numeric,
              b_int integer,
              b_int_name text,
              b_int_age numeric,
              b_age numeric,
              b_prop numeric,
              b_plat numeric,
              b_plng numeric,
              clat numeric,
              clng numeric,
              color text,
              text_color text,
              units_above text,
              units_below text,
              pbdb_collections integer,
              pbdb_occurrences integer,
              age text,
              age_id integer,
              epoch text,
              epoch_id integer,
              period text,
              period_id integer,
              era text,
              era_id integer,
              eon text,
              eon_id integer
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lookup_units_new (unit_id, col_area, project_id, t_int, t_int_name, t_int_age, t_age, t_prop, t_plat, t_plng, b_int, b_int_name, b_int_age, b_age, b_prop, b_plat, b_plng, clat, clng, color, text_color, units_above, units_below, pbdb_collections, pbdb_occurrences, age, age_id, epoch, epoch_id, period, period_id, era, era_id, eon, eon_id) VALUES (%(unit_id)s, %(col_area)s, %(project_id)s, %(t_int)s, %(t_int_name)s, %(t_int_age)s, %(t_age)s, %(t_prop)s, %(t_plat)s, %(t_plng)s, %(b_int)s, %(b_int_name)s, %(b_int_age)s, %(b_age)s, %(b_prop)s, %(b_plat)s, %(b_plng)s, %(clat)s, %(clng)s, %(color)s, %(text_color)s, %(units_above)s, %(units_below)s, %(pbdb_collections)s, %(pbdb_occurrences)s, %(age)s, %(age_id)s, %(epoch)s, %(epoch_id)s, %(period)s, %(period_id)s, %(era)s, %(era_id)s, %(eon)s, %(eon_id)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lookup_units_new (project_id);
            CREATE INDEX ON macrostrat.lookup_units_new (t_int);
            CREATE INDEX ON macrostrat.lookup_units_new (b_int);
        """,
        "process": """

        """
    },

    "lookup_unit_attrs_api": {
        "dump": """
            SELECT unit_id, lith, environ, econ, measure_short, measure_long
            FROM lookup_unit_attrs_api
        """,
        "create": """
            CREATE TABLE macrostrat.lookup_unit_attrs_api_new (
              unit_id integer NOT NULL,
              lith json,
              environ json,
              econ json,
              measure_short json,
              measure_long json
            );
        """,
        "insert": """
            INSERT INTO macrostrat.lookup_unit_attrs_api_new (unit_id, lith, environ, econ, measure_short, measure_long) VALUES (%(unit_id)s, %(lith)s::json, %(environ)s::json, %(econ)s::json, %(measure_short)s::json, %(measure_long)s::json)
        """,
        "index": """
            CREATE INDEX ON macrostrat.lookup_unit_attrs_api_new (unit_id);
        """,
        "process": """

        """
    },

    "environs": {
        "dump": """
            SELECT id, environ, environ_type, environ_class, environ_color
            FROM environs
        """,
        "create": """
            CREATE TABLE macrostrat.environs_new (
              id integer NOT NULL PRIMARY KEY,
              environ text,
              environ_type text,
              environ_class text,
              environ_color text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.environs_new (id, environ, environ_type, environ_class, environ_color) VALUES (%(id)s, %(environ)s, %(environ_type)s, %(environ_class)s, %(environ_color)s)
        """,
        "index": "",
        "process": """

        """
    },

    "econs": {
        "dump": """
            SELECT id, econ, econ_type, econ_class, econ_color
            FROM econs
        """,
        "create": """
            CREATE TABLE macrostrat.econs_new (
              id integer NOT NULL PRIMARY KEY,
              econ text,
              econ_type text,
              econ_class text,
              econ_color text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.econs_new (id, econ, econ_type, econ_class, econ_color) VALUES (%(id)s, %(econ)s, %(econ_type)s, %(econ_class)s, %(econ_color)s)
        """,
        "index": "",
        "process": """

        """
    },

    "unit_liths": {
        "dump": """
            SELECT id, lith_id, unit_id, prop, dom, comp_prop, mod_prop, toc, ref_id, date_mod
            FROM unit_liths
        """,
        "create": """
            CREATE TABLE macrostrat.unit_liths_new (
              id integer NOT NULL PRIMARY KEY,
              lith_id integer,
              unit_id integer,
              prop text,
              dom text,
              comp_prop numeric,
              mod_prop numeric,
              toc numeric,
              ref_id integer,
              date_mod text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_liths_new (id, lith_id, unit_id, prop, dom, comp_prop, mod_prop, toc, ref_id, date_mod) VALUES (%(id)s, %(lith_id)s, %(unit_id)s, %(prop)s, %(dom)s, %(comp_prop)s, %(mod_prop)s, %(toc)s, %(ref_id)s, %(date_mod)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_liths_new (lith_id);
            CREATE INDEX ON macrostrat.unit_liths_new (unit_id);
            CREATE INDEX ON macrostrat.unit_liths_new (ref_id);
        """,
        "process": """

        """
    },

    "unit_lith_atts": {
        "dump": """
            SELECT id, unit_lith_id, lith_att_id, ref_id, date_mod
            FROM unit_liths_atts
        """,
        "create": """
            CREATE TABLE macrostrat.unit_lith_atts_new (
              id integer NOT NULL PRIMARY KEY,
              unit_lith_id integer,
              lith_att_id integer,
              ref_id integer,
              date_mod text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_lith_atts_new (id, unit_lith_id, lith_att_id, ref_id, date_mod) VALUES (%(id)s, %(unit_lith_id)s, %(lith_att_id)s, %(ref_id)s, %(date_mod)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_lith_atts_new (unit_lith_id);
            CREATE INDEX ON macrostrat.unit_lith_atts_new (lith_att_id);
            CREATE INDEX ON macrostrat.unit_lith_atts_new (ref_id);
        """,
        "process": """

        """
    },

    "unit_econs": {
        "dump": """
            SELECT id, unit_id, econ_id, ref_id, date_mod
            FROM unit_econs
        """,
        "create": """
            CREATE TABLE macrostrat.unit_econs_new (
              id integer NOT NULL PRIMARY KEY,
              unit_id integer,
              econ_id integer,
              ref_id integer,
              date_mod text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_econs_new (id, unit_id, econ_id, ref_id, date_mod) VALUES (%(id)s, %(unit_id)s, %(econ_id)s, %(ref_id)s, %(date_mod)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_econs_new (econ_id);
            CREATE INDEX ON macrostrat.unit_econs_new (unit_id);
            CREATE INDEX ON macrostrat.unit_econs_new (ref_id);
        """,
        "process": """

        """
    },

    "unit_environs": {
        "dump": """
            SELECT id, unit_id, environ_id, ref_id, date_mod
            FROM unit_environs
        """,
        "create": """
            CREATE TABLE macrostrat.unit_environs_new (
              id integer NOT NULL PRIMARY KEY,
              unit_id integer,
              environ_id integer,
              ref_id integer,
              date_mod text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.unit_environs_new (id, unit_id, environ_id, ref_id, date_mod) VALUES (%(id)s, %(unit_id)s, %(environ_id)s, %(ref_id)s, %(date_mod)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.unit_environs_new (environ_id);
            CREATE INDEX ON macrostrat.unit_environs_new (unit_id);
            CREATE INDEX ON macrostrat.unit_environs_new (ref_id);
        """,
        "process": """

        """
    },

    "autocomplete": {
        "dump": """
            SELECT id, name, type, category
            FROM autocomplete
        """,
        "create": """
            CREATE TABLE macrostrat.autocomplete_new (
              id integer NOT NULL,
              name text,
              type text,
              category text
            );
        """,
        "insert": """
            INSERT INTO macrostrat.autocomplete_new (id, name, type, category) VALUES (%(id)s, %(name)s, %(type)s, %(category)s)
        """,
        "index": """
            CREATE INDEX ON macrostrat.autocomplete_new (id);
            CREATE INDEX ON macrostrat.autocomplete_new (name);
            CREATE INDEX ON macrostrat.autocomplete_new (type);
            CREATE INDEX ON macrostrat.autocomplete_new (category);
        """,
        "process": """

        """
    },
})
