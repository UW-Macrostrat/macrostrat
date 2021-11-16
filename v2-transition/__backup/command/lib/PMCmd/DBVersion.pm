#
# Paleobiology Database installation and update command
# 
# This module implements routines to update an earlier version of the Paleobiology Database into
# the current schema. The main routine is called whenever the entire database contents are loaded
# from a remote site or a dump file.
# 
# Author: Michael McClennen
# Created: 2019-12-13


use strict;

package PMCmd::DBVersion;

use parent 'Exporter';

use PMCmd::Config qw(%CONFIG AskChoice);
use PMCmd::System qw( PrintDebug SystemDockerCompose CaptureDockerCompose SystemCommand CaptureCommand);

use Scalar::Util qw(reftype);
use Carp qw(carp croak);

our (@EXPORT_OK) = qw(UpdateDatabaseSchema ExecutiveCommand ExecutiveQuery);


# UpdateDatabaseSchema ( dbname )
# 
# This routine checks to see whether the current database schema matches the schema expected by
# the API. If not, it does its best to correct that, and prints warning messages to help the user
# understand what else is necessary.

my ($MYSQL_ERRORS);

sub UpdateDatabaseSchema {

    my ($dbname) = @_;
    
    unless ( $dbname )
    {
	$dbname = AskChoice("Choose database to check:", { default => 1 },
			    "1", "pbdb", "2", "pbdb_wing");
    }
    
    if ( $dbname eq 'pbdb' )
    {
	Update_pbdb();
    }
    
    elsif ( $dbname eq 'pbdb_wing' )
    {
	print "There are no updates to 'pbdb_wing'.\n";
    }

    elsif ( $dbname eq 'macrostrat' )
    {
	print "There are no updates to 'macrostrat'.\n";
    }
    
    elsif ( $dbname )
    {
	print "Unrecognized database '$dbname'\n";
    }
    
    return;
}


sub Update_pbdb {
    
    $MYSQL_ERRORS = 0;
    
    print "\nChecking the database schema and bringing it up to date if necessary...\n\n";
    
    print "  Table 'session_data':\n\n";
    
    my ($session_table) = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'session_data'");
    
    if ( $session_table =~ /session_data/ )
    {
	ExecutiveCommand('pbdb', "ALTER TABLE session_data ADD COLUMN IF NOT EXISTS password_hash varchar(50) null after user_id");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data ADD COLUMN IF NOT EXISTS ip_address varchar(80) null after password");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data ADD COLUMN IF NOT EXISTS expire_days int unsigned NOT NULL DEFAULT '1'");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data ADD COLUMN IF NOT EXISTS created_date timestamp not null default current_timestamp() after record_date");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS authorizer");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS enterer");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS roles");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS marine_invertebrate");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS micropaleontology");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS paleobotany");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS taphonomy");
	
	ExecutiveCommand('pbdb', "ALTER TABLE session_data DROP COLUMN IF EXISTS vertebrate");
    }

    else
    {
	ExecutiveCommand('pbdb', "CREATE TABLE session_data (
  `session_id` varchar(80) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `password_hash` varchar(50) NOT NULL DEFAULT '',
  `ip_address` varchar(80) NOT NULL DEFAULT '',
  `role` varchar(20) DEFAULT NULL,
  `reference_no` int(11) DEFAULT NULL,
  `queue` varchar(255) DEFAULT NULL,
  `record_date` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_date` timestamp NOT NULL DEFAULT current_timestamp(),
  `expire_days` int(11) NOT NULL DEFAULT 1,
  `superuser` tinyint(1) DEFAULT 0,
  `authorizer_no` int(10) NOT NULL DEFAULT 0,
  `enterer_no` int(10) NOT NULL DEFAULT 0,
  PRIMARY KEY (`session_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
    
    print "  Table 'table_permissions':\n\n";
    
    my ($perm_table) = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'table_permissions'");
    
    if ( $perm_table =~ /table_permissions/ )
    {
	ExecutiveCommand('pbdb', "ALTER TABLE table_permissions ADD COLUMN IF NOT EXISTS permission set('none','view','post','modify','delete','insert_key','admin') NOT NULL after table_name");
    }
    
    else
    {
	ExecutiveCommand('pbdb', "CREATE TABLE `table_permissions` (
  `permission_no` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `person_no` int(10) unsigned NOT NULL,
  `table_name` varchar(80) NOT NULL,
  `permission` set('none','view','post','modify','delete','insert_key','admin') NOT NULL,
  PRIMARY KEY (`permission_no`),
  KEY `person_no` (`person_no`,`table_name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8");
    }
    
    print "  Table 'authorities':\n";

    ExecutiveCommand('pbdb', "ALTER TABLE authorities MODIFY COLUMN orig_no int unsigned NOT NULL DEFAULT '0'");
    
    print "  Table 'refs':\n";
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.refs MODIFY COLUMN publication_type enum('journal article','book','book chapter','book/book chapter','serial monograph','compendium','Ph.D. thesis','M.S. thesis','abstract','guidebook','news article','unpublished')");
    
    print "  Table 'specimens':\n";
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.specimens ADD COLUMN IF NOT EXISTS specelt_no int unsigned NOT NULL DEFAULT '0' AFTER specimen_id");
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.table_permissions ADD COLUMN IF NOT EXISTS permission set('', 'none','view','post','modify','delete','insert_key','admin') NOT NULL DEFAULT ''");
    
    print "  Table 'table_permissions':\n";
    
    my $tperms_list = ExecutiveQuery('pbdb', "SHOW CREATE TABLE pbdb.table_permissions");

    if ( $tperms_list =~ /\`role\`/ )
    {
	ExecutiveCommand('pbdb', "UPDATE pbdb.table_permissions SET permission = role");
	
	ExecutiveCommand('pbdb', "ALTER TABLE pbdb.table_permissions DROP COLUMN IF EXISTS role");
    }

    print "  Table 'collections':\n";
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.collections MODIFY COLUMN environment enum('marine indet.','terrestrial indet.','carbonate indet.','peritidal','shallow subtidal indet.','open shallow subtidal','lagoonal/restricted shallow subtidal','sand shoal','reef, buildup or bioherm','perireef or subreef','intrashelf/intraplatform reef','platform/shelf-margin reef','slope/ramp reef','basin reef','deep subtidal ramp','deep subtidal shelf','deep subtidal indet.','offshore ramp','offshore shelf','offshore indet.','slope','basinal (carbonate)','basinal (siliceous)','marginal marine indet.','paralic indet.','lagoonal','coastal indet.','foreshore','shoreface','transition zone/lower shoreface','offshore','deltaic indet.','delta plain','interdistributary bay','delta front','prodelta','deep-water indet.','submarine fan','basinal (siliciclastic)','fluvial-lacustrine indet.','fluvial indet.','\"channel\"','channel lag','coarse channel fill','fine channel fill','\"floodplain\"','wet floodplain','dry floodplain','levee','crevasse splay','lacustrine indet.','lacustrine - large','lacustrine - small','pond','crater lake','karst indet.','fissure fill','cave','sinkhole','eolian indet.','dune','interdune','loess','fluvial-deltaic indet.','estuary/bay','lacustrine deltaic indet.','lacustrine delta plain','lacustrine interdistributary bay','lacustrine delta front','lacustrine prodelta','alluvial fan','glacial','mire/swamp','spring','tar') NULL");
    
    print "  Fixing defaults on 'created' fields:\n";
    
    foreach my $tn ( qw(collections occurrences refs specimens authorities opinions) )
    {
	ExecutiveCommand('pbdb', "UPDATE pbdb.$tn SET created = '0000-00-00' WHERE created is null");
	ExecutiveCommand('pbdb', "ALTER TABLE pbdb.$tn MODIFY COLUMN created datetime NOT NULL DEFAULT CURRENT_TIMESTAMP");
    }
    
    print "  Table 'eduresource_queue':\n";
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.eduresource_queue MODIFY COLUMN description text NOT NULL DEFAULT ''");
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.eduresource_queue MODIFY COLUMN authorizer_no int unsigned NOT NULL DEFAULT '0'");
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.eduresource_queue MODIFY COLUMN enterer_no int unsigned NOT NULL DEFAULT '0'");
    
    ExecutiveCommand('pbdb', "ALTER TABLE pbdb.eduresource_queue MODIFY COLUMN modifier_no int unsigned NOT NULL DEFAULT '0'");

    print "  Checking for timescale tables:\n";
    
    my ($timescale_list) = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'timescale%'");
    my $missing;
    
    foreach my $tn ( qw(timescales timescale_bounds timescale_ints timescale_fix) )
    {
	unless ( $timescale_list =~ /$tn/ )
	{
	    print "    MISSING TABLE: $tn\n";
	    $missing++;
	}
    }
    
    if ( $missing )
    {
	print "  You will need to dump these missing tables from teststrata.geology.wisc.edu or\n";
	print "  some other server where they occur, and load them into this database.\n";
    }
    
    if ( $MYSQL_ERRORS )
    {
	print "\nERRORS OCCURRED DURING THIS EXECUTION.\n\n";
	print "$MYSQL_ERRORS command(s) did not execute correctly.\n";
	print "You may want to try diagnosing this problem and then re-run\n";
	print "the command 'pbdb update database schema' once you think you\n";
	print "have fixed it.\n";
    }
}


sub ExecutiveCommand {
    
    my ($database, $command) = @_;
    
    unless ( $database && $command )
    {
	print "ERROR: no database was specified.\n";
	return;
    }
    
    my $execuser = $CONFIG{exec_username};
    my $execpwd = $CONFIG{exec_password};
    my $service = $CONFIG{database_container} || 'mariadb';
    
    # my $show_command = length($command) < 400 ? $command : substr($command,0,400) . '...';
    
    # $command =~ s{'}{'\\''}g;
    # $command =~ s{'\\'''\\''}{'\\'\\''}g;
    
    print "    $command\n";
    
    $command .= "; select row_count() as 'Affected rows'";
    
    my $result = CaptureCommand('docker-compose', 'exec', $service, 'mysql', '--batch',
				"--user=$execuser", "--password=$execpwd", "--database=$database", "-e", $command);
    
    $MYSQL_ERRORS++ unless $PMCmd::System::RC;
    
    return unless defined $result;
    
    if ( $result =~ /Affected rows\s+(\d+)/m )
    {
	print "      Affected rows: $1\n";
    }

    else
    {
	print $result;
    }
}


sub ExecutiveQuery {
    
    my ($database, $command) = @_;

    return '' unless $database && $command;
    
    my $execuser = $CONFIG{exec_username};
    my $execpwd = $CONFIG{exec_password};
    my $service = $CONFIG{database_container} || 'mariadb';
    
    # $command =~ s{'}{'\\''}g;
    # $command =~ s{'\\'''\\''}{'\\'\\''}g;
    
    my $result = CaptureCommand('docker-compose', 'exec', $service, 'mysql', '--batch', "--user=$execuser", "--password=$execpwd", "--database=$database", '-e', $command);
    
    return $result;
}


1;
