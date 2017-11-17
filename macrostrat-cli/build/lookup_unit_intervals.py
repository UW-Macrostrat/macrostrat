class LookupUnitIntervals:
    meta = {
        'mariadb': True,
        'pg': False
    }
    def build(my_cur, my_conn):
        # Copy structure into new table
        my_cur.execute("CREATE TABLE lookup_unit_intervals_new LIKE lookup_unit_intervals")

        # initial query
        my_cur.execute("""
            SELECT units.id, FO, LO, f.age_bottom, f.interval_name fname, f.age_top FATOP, l.age_top, l.interval_name lname, min(u1.t1_age) AS t_age, max(u2.t1_age) AS b_age
            FROM units
            JOIN intervals f on FO = f.id
            JOIN intervals l ON LO = l.id
            LEFT JOIN unit_boundaries u1 ON u1.unit_id = units.id
            LEFT JOIN unit_boundaries u2 ON u2.unit_id_2 = units.id
            GROUP BY units.id
        """)
        numrows = my_cur.rowcount
        row = my_cur.fetchall()

        # initialize arrays
        r2 = {}
        r3 = {}
        r4 = {}
        r5 = {}
        r6 = {}
        rLO = {}
        rFO = {}

        # handle each unit
        for x in xrange(0,numrows):
        	# Use this as the parameters for most of the queries
        	params = {
        		"age_bottom": row[x]["age_bottom"],
        		"age_top": row[x]["age_top"]
        	}

        	my_cur.execute("""
        		SELECT interval_name,intervals.id from intervals
        		JOIN timescales_intervals ON intervals.id = interval_id
        		JOIN timescales on timescale_id = timescales.id
        		WHERE timescale = 'international epochs'
        			AND %(age_bottom)s > age_top
        			AND %(age_bottom)s <= age_bottom
        			AND %(age_top)s < age_bottom
        			AND %(age_top)s >= age_top
        	""", params)
        	row2 = my_cur.fetchone()

        	if row2 is None:
        		r2['interval_name'] = ''
        		r2['id'] = 0
        	else:
        		r2['interval_name'] = row2['interval_name']
        		r2['id'] = row2['id']

        	my_cur.execute("""
        		SELECT interval_name, intervals.id from intervals
        		JOIN timescales_intervals ON intervals.id = interval_id
        		JOIN timescales on timescale_id = timescales.id
        		WHERE timescale='international periods'
        			AND %(age_bottom)s > age_top
        			AND %(age_bottom)s <= age_bottom
        			AND %(age_top)s < age_bottom
        			AND %(age_top)s >= age_top
        	""", params)
        	row3 = my_cur.fetchone()

        	if row3 is None:
        		r3['interval_name'] = ''
        		r3['id'] = 0
        	else:
        		r3['interval_name'] = row3['interval_name']
        		r3['id'] = row3['id']

        	my_cur.execute("""
        		SELECT interval_name FROM intervals
        		JOIN timescales_intervals ON intervals.id = interval_id
        		JOIN timescales on timescale_id = timescales.id
        		WHERE timescale = 'international periods'
        			AND age_bottom >= %(age_bottom)s
        			AND age_top < %(age_bottom)s
        	""", params)
        	row_period_FO = my_cur.fetchone()

        	if row_period_FO is None:
        		rFO['interval_name'] = ''
        		rFO['id'] = 0
        	else:
        		rFO['interval_name'] = row_period_FO['interval_name']

        	my_cur.execute("""
        		SELECT interval_name FROM intervals
        		JOIN timescales_intervals ON intervals.id = interval_id
        		JOIN timescales on timescale_id = timescales.id
        		WHERE timescale = 'international periods'
        			AND age_bottom > %(age_top)s
        			AND age_top <= %(age_top)s
        	""", params)
        	row_period_LO = my_cur.fetchone()

        	if row_period_LO is None:
        		rLO['interval_name'] = ''
        		rLO['id'] = 0
        	else:
        		rLO['interval_name'] = row_period_LO['interval_name']

        	my_cur.execute("""
        		SELECT interval_name, intervals.id from intervals
        		JOIN timescales_intervals ON intervals.id = interval_id
        		JOIN timescales on timescale_id = timescales.id
        		WHERE timescale = 'international ages'
        			AND %(age_bottom)s > age_top
        			AND %(age_bottom)s <= age_bottom
        			AND %(age_top)s < age_bottom
        			AND %(age_top)s >= age_top
        	""", params)
        	row4 = my_cur.fetchone()

        	if row4 is None:
        		r4['interval_name'] = ''
        		r4['id'] = 0
        	else:
        		r4['interval_name'] = row4['interval_name']
        		r4['id'] = row4['id']

        	my_cur.execute("""
        		SELECT interval_name,intervals.id from intervals
        		WHERE interval_type = 'eon'
        			AND %(age_bottom)s > age_top
        			AND %(age_bottom)s <= age_bottom
        			AND %(age_top)s < age_bottom
        			AND %(age_top)s >= age_top
        	""", params)
        	row5 = my_cur.fetchone()

        	if row5 is None:
        		r5['interval_name'] = ''
        		r5['id'] = 0
        	else:
        		r5['interval_name'] = row5['interval_name']
        		r5['id'] = row5['id']

        	my_cur.execute("""
        		SELECT interval_name, intervals.id from intervals
        		WHERE interval_type = 'era'
        			AND %(age_bottom)s > age_top
        			AND %(age_bottom)s <= age_bottom
        			AND %(age_top)s < age_bottom
        			AND %(age_top)s >= age_top
        	""", params)
        	row6 = my_cur.fetchone()

        	if row6 is None:
        		r6['interval_name'] = ''
        		r6['id'] = 0
        	else:
        		r6['interval_name'] = row6['interval_name']
        		r6['id'] = row6['id']

        	my_cur.execute("""
            INSERT INTO lookup_unit_intervals_new (unit_id, FO_age, b_age, FO_interval, LO_age, t_age, LO_interval, epoch, epoch_id, period, period_id, age,age_id, era, era_id, eon, eon_id, FO_period, LO_period)
            VALUES (%(rx_id)s, %(rx_age_bottom)s, %(rx_b_age)s, %(rx_fname)s, %(rx_age_top)s, %(rx_t_age)s, %(rx_lname)s, %(r2_interval_name)s, %(r2_id)s, %(r3_interval_name)s, %(r3_id)s, %(r4_interval_name)s, %(r4_id)s, %(r6_interval_name)s, %(r6_id)s, %(r5_interval_name)s, %(r5_id)s, %(rFO)s, %(rLO)s )""", {

                "rx_id": row[x]["id"],
                "rx_age_bottom": row[x]["age_bottom"],
                "rx_age_top": row[x]["age_top"],
                "rx_b_age": row[x]["b_age"],
                "rx_t_age": row[x]["t_age"],
                "rx_fname": row[x]["fname"],
                "rx_lname": row[x]["lname"],

                "r2_interval_name": r2["interval_name"],
                "r2_id": r2["id"],

                "r3_interval_name": r3["interval_name"],
                "r3_id": r3["id"],

                "r4_interval_name": r4["interval_name"],
                "r4_id": r4["id"],

                "r5_interval_name": r5["interval_name"],
                "r5_id": r5["id"],

                "r6_interval_name": r6["interval_name"],
                "r6_id": r6["id"],

                "rFO": rFO["interval_name"],
                "rLO": rLO["interval_name"]
          })

        #modifiy results for long-ranging units
        my_cur.execute("UPDATE lookup_unit_intervals_new set period = concat_WS('-',FO_period,LO_period) where period = '' and FO_period not like ''")
        my_cur.execute("UPDATE lookup_unit_intervals_new set period = eon where period = '' and eon = 'Archean'")
        my_cur.execute("UPDATE lookup_unit_intervals_new set period = concat_WS('-', FO_interval, LO_period) where FO_interval = 'Archean'")
        my_cur.execute("UPDATE lookup_unit_intervals_new set period = 'Precambrian' where period = '' and t_age >= 541")


        ## validate results
        my_cur.execute("SELECT count(*) N, (SELECT count(*) from lookup_unit_intervals_new) nn from units")
        row = my_cur.fetchone()
        if row['N'] != row['nn'] :
        	print "ERROR: inconsistent unit count in lookup_unit_intervals_new table"

        # Out with the old, in with the new
        my_cur.execute("""
            ALTER TABLE lookup_unit_intervals RENAME TO lookup_unit_intervals_old;
            ALTER TABLE lookup_unit_intervals_new RENAME TO lookup_unit_intervals;
            DROP TABLE lookup_unit_intervals_old;
        """)
        my_cur.close()
