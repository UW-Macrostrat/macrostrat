UPDATE lookup_units_new
SET period = eon
WHERE period = '' AND eon = 'Archean';

UPDATE lookup_units_new
SET period = 'Precambrian'
WHERE period = '' AND t_age >= 541;

UPDATE lookup_units
SET period = concat_WS('-', (
        SELECT intervals.interval_name
        FROM intervals
        JOIN timescales_intervals ON intervals.id = interval_id
        JOIN timescales on timescale_id = timescales.id
        WHERE timescale = 'international periods'
        AND age_top <= (SELECT age_top FROM intervals WHERE id = b_int)
        AND age_bottom >= (SELECT age_bottom FROM intervals WHERE id = b_int)
    ), (
        SELECT intervals.interval_name
        FROM intervals
        JOIN timescales_intervals ON intervals.id = interval_id
        JOIN timescales on timescale_id = timescales.id
        WHERE timescale = 'international periods'
        AND age_top <= (SELECT age_top FROM intervals WHERE id = t_int)
        AND age_bottom >= (SELECT age_bottom FROM intervals WHERE id = t_int)
    ))
WHERE period = '';

TRUNCATE TABLE lookup_units;
INSERT INTO lookup_units SELECT * FROM lookup_units_new;
DROP TABLE lookup_units_new;

