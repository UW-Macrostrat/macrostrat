START TRANSACTION;
DROP TABLE IF EXISTS unit_boundaries_backup_recent;
CREATE TABLE unit_boundaries_backup_recent LIKE unit_boundaries;
INSERT INTO unit_boundaries_backup_recent SELECT * FROM unit_boundaries;

DROP TABLE unit_boundaries;

CREATE TABLE IF NOT EXISTS `unit_boundaries` (
  `id` mediumint(8) unsigned NOT NULL AUTO_INCREMENT,
  `t1` mediumint(8) unsigned NOT NULL,
  `t1_prop` decimal(6,5) NOT NULL,
  `t1_age` decimal(8,4) NOT NULL,
  `unit_id` mediumint(8) unsigned NOT NULL,
  `unit_id_2` mediumint(8) unsigned NOT NULL,
  `section_id` mediumint(8) unsigned NOT NULL,
  `boundary_type` enum('','unconformity','conformity','fault','disconformity','non-conformity','angular unconformity') NOT NULL DEFAULT '',
  `boundary_status` enum('','modeled','updated','spike') NOT NULL DEFAULT 'modeled',
  PRIMARY KEY (`id`),
  KEY `t1` (`t1`),
  KEY `unit_id` (`unit_id`),
  KEY `unit_id_2` (`unit_id_2`),
  KEY `section_id` (`section_id`)
) ENGINE=MyISAM AUTO_INCREMENT=46330 DEFAULT CHARSET=latin1;

SET @csv := concat(@directory, '/scripts/UB_full_V5V3_sectionbump.csv');

LOAD DATA INFILE '@csv' 
INTO TABLE unit_boundaries 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(t1,t1_prop,t1_age,unit_id,unit_id_2,section_id);

COMMIT;
