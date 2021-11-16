#
# Paleobiology Database tasks
# 
# This module implements tasks that are useful in maintaining the Paleobiology Database. It
# is designed to function as part of the PBDB/Macrostrat status and control command.
# 
# Author: Michael McClennen
# Created: 2020-07-13


use strict;

package PMCmd::PBTasks;

use parent 'Exporter';

use PMCmd::Config qw($MAIN_PATH $COMMAND $DEBUG %CONFIG %BACKUP_NAME %COMPONENT
		     $LOCAL_CONFIG ReadLocalConfig);
use PMCmd::System qw(GetContainerID SystemCommand CaptureCommand ResultCode);
use PMCmd::Command qw(TaskConfigSelect TaskErrorMessage);

use POSIX qw(tzname);

our %TASK = ( 'build-tables' => 'PMCmd::PBTasks::BuildTablesTask',
	      'paleo-coords' => 'PMCmd::PBTasks::PaleoCoordsTask',
	      'rotate-logs' => 'PMCmd::PBTasks::RotateLogsTask',
	      'backup' => 'PMCmd::PBTasks::BackupTask',
	      'remote-sites' => 'PMCmd::PBTasks::RemoteUpdateTask',
	      'test' => 'PMCmd::PBTasks::TestTask' );

our %TASK_CONFIG = ( 'backup' => 'pbdb_backup',
		     'remote-sites' => 'pbdb_remote_sites',
		     'rotate-logs' => 'log_rotation' );

our %CDOC = ( 'build-tables' => "Build the derived tables from the core tables.",
	      'paleo-coords' => "Compute paleocoordinates for fossil collections.",
	      'rotate-logs' => "Rename log files and restart the processes that generate them.",
	      'backup' => "Dump the database tables to disk files.",
	      'remote-sites' => "Copy the latest database dumps to remote sites",
	      'test' => "Print out a test message, and do nothing else" );

our %LDOC;

our @CLIST = ( 'build-tables', 'paleo-coords', 'rotate-logs', 'backup', 'remote-sites', 'test' );


$LDOC{'build-tables'} = <<EndBuild;

Usage:  {NAME} do build-tables(options)

Execute the script bin/build_tables.pl in the pbapi container. If you do not
specify any tables to back up, the option --nightly will be added by default.

Options:

  log, log=filename    Append a list of build actions to the default log file
                       logs/build_log, or else to a specified file.

  stdout               Write the list of build actions to standard output. This
                       is the default unless the --log option is given after
                       'do'. There will be several hundred lines of output
                       to stdout, and will be several hundred lines for a
                       full nightly build.

  test                 Print a test message as directed by the output 
                       options given above and then exit.

  error                Throw an exception, and do nothing else. This is
                       for debugging purposes only.

  c                    Build the collections tables

  m                    Build the occurrences tables

  t                    Build the taxonomy tables

  y                    Build the old taxonomy tables for Classic

  nightly              Build all of the tables listed above

If no tables are specified, 'nightly' is the default. You can combine any of
cmty into one argument.

EndBuild

# BuildTablesTask ( )
# 
# This task is designed to be executed on a nightly basis to rebuild the PBDB derived tables from
# the core tables.

sub BuildTablesTask {
    
    my ($task, @args) = @_;
    
    my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
    my $container = join('_', $1, 'pbapi', 1);
    
    my @cmdopts;
    my $has_spec;

    foreach my $opt ( @args )
    {
	if ( $opt =~ qr{ ^ -* ( nightly | test | error | [cmty]+ ) $ }xs )
	{
	    $has_spec = 1;
	    
	    if ( $1 eq 'nightly' || $1 eq 'test' || $1 eq 'error' )
	    {
		push @cmdopts, "--$1";
	    }
	    
	    else
	    {
		push @cmdopts, "-$1";
	    }
	}

	elsif ( $opt =~ qr{ ^ -* stdout $ }xs )
	{
	    # ignore
	}
	
	elsif ( $opt =~ qr{ ^ -* log (?: = (.*) )? $ }xs )
	{
	    # my $logfile = $1 || $CONFIG{build_log_file} || 'build_log';
	    # push @cmdopts, "--log=logs/$logfile";
	}
	
	elsif ( $opt =~ qr{ ^ -* ( .+ ) $ }xs )
	{
	    push @cmdopts, "--$1";
	}
    }
    
    push @cmdopts, '--nightly' unless $has_spec;
    
    SystemCommand('docker', 'exec', $container, 'bin/build_tables.pl', @cmdopts);
    return ResultCode();
}


$LDOC{'paleo-coords'} = <<EndPaleo;

Usage:  {NAME} do paleo-coords(options)

Execute the script bin/paleocoords.pl in the pbapi container. If no options
are specified, paleocoordinates will be computed for all collections that do not have
them, or whose modern geographic location has been modified. If this task is executed
periodically, those will be the collections that have been added or whose location
has been modified since the last execution.

Options:

  log, log=filename    Append the output of this task to the default log file
                       logs/pbdb-new/paleocoords_log, or else to a specified file.

  stdout               Direct the output of this task to standard output. This
                       is the default unless the --log option is given after 'do'.

  test                 Print a test message as directed by the output 
                       options given above and then exit.

  error                Throw an exception, and do nothing else. This is
                       for debugging purposes only.

  verbose              Generate extra output for debugging.

  debug                Print every SQL statement before executing it.

  db=dbname            Update paleocoordinates in a database other than 'pbdb'.

  update-all           Recompute all paleocoordinates, or all of them in the
                       age range specified by min-age and max-age. By default,
                       only collections without any paleocoordinates are updated.

  clear-all            Clear all paleocoordinates, or all of them in the age
                       range specified by min-age and max-age.

  coll=identifier(s)   Update the paleocoordinates for just the specified
                       collection(s). You can specify one or more collection
                       identifiers, as a comma-separated list of numbers.

  min-age=age          Update or clear only paleocoordinates whose age is
                       greater than or equal to the specified value in Ma.

  max-age=age          Update or clear only paleocoordinates whose age is
                       less than or equal to the specified value in Ma.

EndPaleo

# PaleoCoordsTask ( )
# 
# This task is designed to be executed several times each day to compute paleocoordinates for
# collections that have been newly entered or have had their modern coordinates changed.

sub PaleoCoordsTask {
    
    my ($task, @args) = @_;
    
    my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
    my $container = join('_', $1, 'pbapi', 1);
    
    my @cmdopts;
    my $has_spec;

    foreach my $opt ( @args )
    {
	if ( $opt =~ qr{ ^ -* ( verbose | debug | test | error | update-all | clear-all ) $ }xs )
	{
	    push @cmdopts, "--$1";
	}
	
	elsif ( $opt =~ qr{ ^ -* stdout $ }xs )
	{
	    # ignore
	}
	
	elsif ( $opt =~ qr{ ^ -* log (?: = (.*) )? $ }xs )
	{
	    my $logfile = $1 || $CONFIG{paleocoord_log_file} || 'paleocoord_log';
	    push @cmdopts, "--log=logs/$logfile";
	}
	
	elsif ( $opt =~ qr{ ^ -* ( .+ ) $ }xs )
	{
	    push @cmdopts, "--$1";
	}
    }
    
    SystemCommand('docker', 'exec', $container, 'bin/paleocoords.pl', @cmdopts);
    return ResultCode();
}


$LDOC{'backup'} = <<EndBackup;

Usage:  {NAME} do backup[(options)]

Use the 'mysqldump' command to dump the PBDB databases to files on disk. The
dump files will be created in the directory specified by the configuration
setting 'backup_dir', unless you specify otherwise with the 'dir' option.

Options:

  dir=path             Create the dump files in the specified directory. A
                       relative path is evaluated from the project root.

  nodate               Any occurrence of SELECT or DATE in a filename will be
                       replaced by 'latest' instead of by the current date.

  log, log=filename    Append the output of this task to the default log file
                       logs/backup_log, or to the specified file.

  stdout               Direct the output of this task to standard output. This is
                       the default, but you can specify it explicitly to override
                       the --log option of the 'do' command. 

  nogzip               Do not gzip the dump files, instead write them uncompressed.
                       The .gz suffix will NOT be added.

  filter=command       Pipe the output of 'mysqldump' through the specified command
                       before sending it to gzip or writing it to disk. This can be
                       used to remove specific portions of the dump, to transform it
                       so that it is properly formatted for MySQL or some other
                       DBMS, etc.

  pbdb=filename        Dump the database 'pbdb'. If no filename is specified,
                       The default name is 'pbdb-backup-latest'. If 'date' is
                       also specified, the default name is 'pbdb-backup-YYYYMMDD'
                       with 'pbdb-backup-latest' symlinked to it.

  wing=filename        Dump the database 'pbdb_wing', using the same pattern
                       as above with 'pbdb-wing-backup-latest'.

  core=filename        Dump the core tables from the database 'pbdb', using the
                       same pattern as above with 'pbdb-core-backup-latest'.

  config               Execute this task using the options specified under the
                       configuration setting 'pbdb_backup'. If this setting is
                       a list, it is executed once for each list element. The
                       list values must be strings of space-separated options.

If no databases are specified, then 'pbdb' and 'pbdb_wing' will be dumped
according to the rules given above.

Any instance of 'DATE' in a filename will be replaced by the current date in
the format given above. Any instance of 'SELECT' will be replaced by the
current date if the 'date' option is given, and by 'latest' otherwise.

The dump files will all be gzip-compressed by default, and the suffix '.gz'
will be added to all filenames. This can be overridden using the option 'raw'.

EndBackup


# BackupTask ( )
#
# This task is designed to be executed on a nightly basis, after the build-tables task.
# It dumps the PBDB databse tables to disk.

sub BackupTask {

    my ($cmd, @args) = @_;
    
    my $start_time = time;
    
    my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
    my ($container_name) = $CONFIG{database_container} || 'mariadb';
    my $container = join('_', $base_name, $container_name, 1);
    
    my ($opt_dir, $opt_gzip, $opt_gmt, $opt_nodate, $opt_filter, $opt_test);
    my (@subtasks);
    
    # Evaluate the arguments one by one.

    my @output_list;
    
    foreach my $opt ( @args )
    {
	if ( ref $opt eq 'HASH' )
	{
	    push @subtasks, $opt;
	    push @output_list, ($opt->{name} || $opt->{dbname} || 'unknown');
	}
	
	elsif ( $opt =~ qr{ ^ -* ( dir | log | stdout | filter ) (?: = (.*) )? $ }xs )
	{
	    $opt_dir = $2 if $1 eq 'dir';
	    $opt_filter = $2 if $1 eq 'filter';
	    # log and stdout are processed in Command.pm and are ignored.
	    push @output_list, $opt;
	}
	
	elsif ( $opt =~ qr{ ^ -* ( nodate | gzip | nogzip | gmt | test ) $ }xs )
	{
	    $opt_nodate = 1 if $1 eq 'nodate';
	    $opt_gzip = 1 if $1 eq 'gzip';
	    $opt_gzip = 0 if $1 eq 'nogzip';
	    $opt_gmt = 1 if $1 eq 'gmt';
	    $opt_test = 1 if $1 eq 'test';
	    push @output_list, $opt;
	}
	
	elsif ( $opt =~ qr{ ^ -* ( \w+ ) (?: = (.*) )? $ }xs )
	{
	    if ( $1 eq 'nightly' )
	    {
		push @subtasks, { select => 'pbdb' };
		push @subtasks, { select => 'wing' };
		push @output_list, $opt;
	    }
	    
	    else
	    {
		my $subtask = { select => $1 };
		$subtask->{filename} = $2 if $2;
		push @subtasks, $subtask;
		push @output_list, $opt;
	    }
	}
	
	else
	{
	    die "ERROR: unrecognized argument '$opt'\n";
	}
    }
    
    # Print out a header, including a timestamp.
    
    my $now = $opt_gmt ? gmtime : localtime;
    my ($tz) = tzname;
    
    $tz = 'UTC' if $tz eq 'GMT' || $opt_gmt;
    
    print "------------------------------------------------------------\n";
    print "Initiating backup at $now $tz\n";
    print "Arguments: " . join(' ', @output_list) . "\n";
    
    # Grab the separate components of the date in case we need them, and set default names.
    
    my ($s, $m, $h, $day, $mon, $year) = $opt_gmt ? gmtime(time) : localtime(time);
    
    $mon = $mon + 1;
    $year = $year + 1900 if $year < 1900;
    
    my $datestring = sprintf("%4d%02d%02d", $year, $mon, $day);
    
    # Make sure that latest version of the configuration file is copied in, so that we have the
    # right username and password for mysqldump to use.
    
    if ( -e "mariadb/maridb.conf.d/backup.cnf" )
    {
	SystemCommand("docker cp mariadb/mariadb.conf.d/backup.cnf paleobiodb_mariadb_1:/etc/mysql/mariadb.conf.d/backup.cnf");
    }
    
    # Hardcoded backkup for databases we know about.

    my %hard_dbargs = ( 'pbdb' => 'pbdb', 'wing' => 'pbdb_wing', 'pbdb_wing' => 'pbdb_wing',
			'core' => 'pbdb authorities collections ecotaph intervals interval_lookup measurements occurrences opinions permissions person pubs refs reidentifications secondary_refs specimens taxa_tree_cache' );
    
    # Now execute all of the specified subtasks in order.
    
    my $rc = 0;
    
  SUBTASK:
    foreach my $subtask ( @subtasks )
    {
	if ( my $select = $subtask->{select} )
	{
	    my $config = TaskConfigSelect($TASK_CONFIG{backup}, $select);

	    if ( $config )
	    {
		my $filename = $subtask->{filename};
		
		$subtask = $config;
		$subtask->{filename} = $filename if $filename;
	    }
	}
	
	my $name = $subtask->{name} || $subtask->{select};
	my $dbargs = $subtask->{dbname} || $CONFIG{backup_database}{$name} || $hard_dbargs{$name};
	
	unless ( $dbargs )
	{
	    my ($username, $password) = ($CONFIG{pbdb_username}, $CONFIG{pbdb_password});
	    
	    my $dbcheck = CaptureCommand('docker', 'exec', $container, 'mysql',
					 "--user=$username", "--password=$password", '-e', "show databases like '$name'");
	    
	    if ( $dbcheck && $dbcheck =~ /$name/ )
	    {
		$dbargs = $name;
	    }
	    
	    else
	    {
		TaskErrorMessage("ERROR: unknown database '$name'\n");
		$rc = 1;
		next SUBTASK;
	    }
	}
	
	# Figure out the filename to which this database will be dumped.
	
	my ($filename, $linkname);
	
	if ( $subtask->{filename} && $subtask->{$filename} ne 'default' )
	{
	    $filename = $subtask->{filename};
	}
	
	elsif ( $name && $CONFIG{backup_filename}{$name} )
	{
	    $filename = $CONFIG{backup_filename}{$name};
	}
	
	unless ( $filename )
	{
	    TaskErrorMessage("ERROR: no default filename was found for '$name'. You must specify one.\n");
	    $rc = 1;
	    next SUBTASK;
	}
	
	# If the 'raw' option was not specified, add the suffix .gz unless the name already ends
	# in that.

	my $no_gzip = defined $opt_gzip && $opt_gzip == 0 || ($subtask->{nogzip} && ! $opt_gzip);
	
	unless ( $no_gzip )
	{
	    $filename .= ".gz" unless $filename =~ /[.]gz$/;
	}
	
	# If the filename has 'SELECT' or 'DATE' in it, that will be substituted with the current
	# date unless the 'nodate' option was given. In that case, it will just have
	# 'latest'. Otherwise, a symlink to the file will be generated using 'latest'.
	
	if ( $filename =~ /DATE|SELECT/ )
	{
	    if ( $opt_nodate )
	    {
		$filename =~ s/DATE|SELECT/latest/;
	    }
	    
	    else
	    {
		$linkname = $filename;
		$linkname =~ s/DATE|SELECT/latest/;
		$filename =~ s/DATE|SELECT/$datestring/;
	    }
	}
	
	# Put the dump file in the proper directory, unless the pathname is absolute.
	
	if ( $filename !~ qr{^/} )
	{
	    if ( $opt_dir && $opt_dir ne 'default' )
	    {
		$opt_dir = "$MAIN_PATH/$opt_dir" unless $opt_dir =~ qr{^/};
		$filename = "$opt_dir/$filename";
		$linkname = "$opt_dir/$linkname" if $linkname;
	    }
	    
	    elsif ( $CONFIG{backup_dir} )
	    {
		$filename = "$CONFIG{backup_dir}/$filename";
		$linkname = "$CONFIG{backup_dir}/$linkname" if $linkname;
	    }
	    
	    else
	    {
		die "ERROR: you must specify a directory, either with 'dir=' or the 'backup_dir' configuration setting\n";
	    }
	}
	
	# Do one more check to make sure that we have a filename to write the backup to.
	
	unless ( $filename )
	{
	    TaskErrorMessage("ERROR: no filename was specified for '$name'\n");
	    next SUBTASK;
	}
	
	# Print out a message indicating what we are doing:
	
	my $label;

	if ( $dbargs =~ qr{ ^ (\S+) \s+ (\S.*) }xs )
	{
	    print "Backing up tables from the database '$1' to $filename...\n";
	    print "  Tables backed up: $2\n";
	}
	
	else
	{
	    print "Backing up the database '$dbargs' to $filename...\n";
	}
	
	# If the target file already exists, rename it using the suffix ".prev". That way, if the
	# current operation fails we will at least still have the old backup file. If there is
	# already a .prev version, delete it.
	
	if ( -e $filename )
	{
	    if ( -e "$filename.prev" )
	    {
		unlink("$filename.prev") ||
		    TaskErrorMessage("WARNING: could not unlink $filename.prev: $!\n");
	    }
	    
	    rename($filename, "$filename.prev") ||
		TaskErrorMessage("WARNING: could not rename $filename to $filename.prev: $!\n");
	}
	
	# Construct the command that we will use to do the backup.

	my $command = "docker exec $container mysqldump --opt --force $dbargs";

	if ( my $filter = $subtask->{filter} || $opt_filter )
	{
	    $command .= " | $filter";
	    print "  Applying filter: $filter\n";
	}
	
	if ( $no_gzip )
	{
	    $command .= " > $filename";
	}
	
	else
	{
	    $command .= " | gzip > $filename";
	}

	# Skip the actuall command if we are in 'test' mode.

	next if $opt_test;
	
	# Otherwise, execute the command.
	
	my $result = SystemCommand($command);
	
	# If the command executes successfully and the resulting filename actually has at least 2k
	# of data in it, then we consider this operation to be successful. We have that minimum
	# data threshold so that if the operation simply generates some error message or a short
	# header without any data, that will count as a failure.
	
	if ( $result && -e $filename && -s $filename > 2048 )
	{
	    # If the operation is a success, we remove the old version of the backup file if any.
	    
	    unlink "$filename.prev";
	    
	    # If this backup file is supposed to have a 'latest' name symlinked to it, do that
	    # now. Remove the existing symlink if any and recreate it to point to the newly
	    # written file.
	    
	    if ( $linkname )
	    {
		print "Making symlink $linkname\n";
		
		if ( -e $linkname || -l $linkname )
		{
		    unlink($linkname) || TaskErrorMessage("WARNING: could not unlink $linkname: $!\n");
		}
		
		symlink($filename, $linkname) ||
		    TaskErrorMessage("WARNING: could not symlink $linkname to $filename: $!\n");
	    }
	}
	
	# If the operation fails and there is a previous version of the backup file, rename that
	# back to the original name. The result is to leave the situation as if the failed oepration had
	# never been carried out.
	
	elsif ( -e "$filename.prev" )
	{
	    print "The dump was not properly created. Restoring the previous version of '$filename'.\n";
	    rename("$filename.prev", $filename) ||
		TaskErrorMessage("WARNING: could not rename $filename.prev to $filename: $!\n");
	}
	
	print "Complete.\n";
	
	$rc = ResultCode() if ResultCode();
    }

    my $elapsed = time - $start_time;
    my $min = int($elapsed/60);
    my $sec = $elapsed % 60;
    print "Elapsed time: $min minutes $sec seconds\n";
    
    return $rc;
}


$LDOC{'remote-sites'} = <<EndRemote;

Usage:  {NAME} do remote-sites[(options)]

Send one or more of the pbdb backup files to remote sites. The default command
to do this is 'scp'. The basic format for a remote destination is:

  username\@hostname:dest_filename

A given file will be copied to that destination as the specified destination
filename.

Options:

  dir=path             Look for files to send in the specified directory. If
                       not given it defaults to the default backup directory,
                       The configuration setting 'backup_dir'.

  log, log=filename    Direct output from this task to the default log file
                       logs/backup_log, or to the specified file.

  stdout               Direct the output of this task to standard output. This is
                       the default, but you can specify it explicitly to override
                       the --log option of the 'do' command. 

  pbdb=remote_dest     Send the latest backup of the database 'pbdb' to the
                       specified remote destination.

  wing=remote_dest     Send the latest backup of the database 'pbdb_wing' to
                       the specified remote destination.

  core=remote_dest     Send the latest backup of the pbdb core tables to
                       the specified remote destination.
  
  gmt                  Log entries will be timestamped using gmt instead of
                       local time.

  config               Execute all of the actions specified by the configuration
                       setting 'pbdb_remote_sites'. This can either be a hash
                       or a list of hashes, with keys matching those listed
                       below.

  database             Specifies which of the databases (as listed above)
                       to send. You can specify either this field or
                       'file', but not both.

  file                 Specifies the exact name of the backup file to send.

  remote               Specifies a remote destination, as above.

  cmd                  Specifies an alternative command to use, instead of
                       "scp". This could be scp with extra arguments, or
                       something else entirely. The string \%local is 
                       replaced with the local filename, and \%remote is
                       replaced with the remote destination.

EndRemote

# RemoteUpdateTask ( )
#
# Send the latest database dumps to remote sites, according to the specified options.

sub RemoteUpdateTask {

    my ($cmd, @args) = @_;
    
    my $start_time = time;
    
    # First, go through the arguments. If one of them is a hashref, it was created using
    # parameters from the configuration file. The rest should be strings.
    
    my ($opt_log, $opt_gmt, $opt_dir, $opt_test);
    my (@subtasks, @output_list);
    
    foreach my $opt ( @args )
    {
	if ( ref $opt eq 'HASH' )
	{
	    push @subtasks, $opt;
	    push @output_list, ($opt->{name} || $opt->{database} || 'unknown');
	}
	
	elsif ( $opt =~ qr{ ^ -* ( log | stdout | dir | gmt | test ) (?: = (.*) )? $ }xs )
	{
	    $opt_gmt = 1 if $1 eq 'gmt';
	    $opt_dir = ($2 || 'default') if $1 eq 'dir';
	    $opt_test = 1 if $1 eq 'test';
	    # log and stdout are ignored
	    push @output_list, $opt;
	}
	
	elsif ( $opt =~ qr{ ^ -* ( database | file | remote | cmd ) (?: = (.*) )? $ }xs )
	{
	    unless ( @subtasks && $subtasks[-1]{cmdline} )
	    {
		push @subtasks, { cmdline => 1 };
	    }
	    
	    $subtasks[-1]{$1} = $2;
	    die "ERROR: you must use $1 as '$1=value'.\n" unless $2;
	    push @output_list, $opt;
	}
	
	elsif ( $opt =~ qr{ ^ ( \w+ ) (?: = (.*) ) $ }xs )
	{
	    unless ( @subtasks && $subtasks[-1]{cmdline} )
	    {
		push @subtasks, { cmdline => 1 };
	    }
	    
	    $subtasks[-1]{database} = $1;
	    $subtasks[-1]{remote} = $2;
	    die "ERROR: you must specify a remote site for '$1'\n" unless $2;
	    push @output_list, $opt;
	}
	
	else
	{
	    die "ERROR: unrecognized argument '$opt'\n";
	}
    }
    
    # Print out a header, including a timestamp.
    
    my $now = $opt_gmt ? gmtime : localtime;
    my ($tz) = tzname;
    
    $tz = 'UTC' if $tz eq 'GMT' || $opt_gmt;
    
    print "------------------------------------------------------------\n";
    print "Initiating remote data transfer at ${now} ${tz}\n";
    print "Arguments: " . join(' ', @output_list) . "\n";
    
    # Now execute all of the specified subtasks in order.
    
    my $rc = 0;
    
  SUBTASK:
    foreach my $subtask ( @subtasks )
    {
	# Start by figuring out what file we are going to send. If it is not specified directly,
	# it must be configured for the specified database name.
	
	my $filename = $subtask->{filename};
	my $database = $subtask->{database};
	
	if ( $filename && $database )
	{
	    TaskErrorMessage("ERROR: You cannot specify both 'filename' and 'database' together\n");
	    $rc = 10;
	    next SUBTASK;
	}
	
	elsif ( ! $filename && ! $database )
	{
	    TaskErrorMessage("ERROR: You must specify either 'filename' or 'database' for each subtask\n");
	    $rc = 10;
	    next SUBTASK;
	}
	
	elsif ( ! $filename && $database )
	{
	    my $config = TaskConfigSelect($TASK_CONFIG{backup}, $database);

	    if ( $config && $config->{filename} )
	    {
		$filename = $config->{filename};
	    }
	    
	    elsif ( $CONFIG{backup_filename}{$database} )
	    {
		$filename = $CONFIG{backup_filename}{$database};
	    }
	}
	
	unless ( $filename )
	{
	    TaskErrorMessage("ERROR: No filename was configured for database '$database'\n");
	    $rc = 10;
	    next SUBTASK;
	}
	
	# Look for the local file in the proper directory, unless the pathname is absolute.
	
	if ( $filename !~ qr{^/} )
	{
	    if ( $opt_dir && $opt_dir ne 'default' )
	    {
		$opt_dir = "$MAIN_PATH/$opt_dir" unless $opt_dir =~ qr{^/};
		$filename = "$opt_dir/$filename";
	    }
	    
	    elsif ( $CONFIG{backup_dir} )
	    {
		$filename = "$CONFIG{backup_dir}/$filename";
	    }
	    
	    else
	    {
		TaskErrorMessage("ERROR: you must specify a directory, either with 'dir=' or the 'backup_dir' configuration setting\n");
		$rc = 10;
		next SUBTASK;
	    }
	}
	
	# Try to find the file in any of its possible variants. If the filename contains either of
	# the strings SELECT or DATE, substitute them with 'latest'. Then check for that name both
	# with and without a .gz suffix.
	
	my $local;

	my @variants;
	
	my $test_name = $filename;
	$test_name =~ s/SELECT|DATE/latest/;

	push @variants, $test_name, "$test_name.gz";
	
	if ( -e $test_name )
	{
	    $local = $test_name;
	}
	
	elsif ( -e "$test_name.gz" )
	{
	    $local = "$test_name.gz";
	}
	
	# If we can't find either of those, try sustituting today's date. Again, check both with
	# and without a .gz suffix.
	
	elsif ( $filename =~ /SELECT|DATE/ )
	{
	    $test_name = $local;
	    
	    my ($s, $m, $h, $day, $mon, $year) = localtime(time);
	    
	    $mon = $mon + 1;
	    $year = $year + 1900 if $year < 1900;
	    
	    my $datestring = sprintf("%4d%02d%02d", $year, $mon, $day);
	    
	    $test_name =~ s/SELECT|DATE/$datestring/;

	    push @variants, $test_name, "$test_name.gz";
	    
	    if ( -e $test_name )
	    {
		$local = $test_name;
	    }
	    
	    elsif ( -e "$test_name.gz" )
	    {
		$local = "$test_name.gz";
	    }
	}

	# If we can't find any of these variants, we cannot send the file.
	
	unless ( $local )
	{
	    TaskErrorMessage("ERROR: could not find any variant of $filename\n");
	    foreach my $f ( @variants )
	    {
		TaskErrorMessage("  $f: not found\n");
	    }
	    $rc = 4;
	    next SUBTASK;
	}
	
	# If the file is not readable, we can stop right now.
	
	unless ( -r $local )
	{
	    TaskErrorMessage("ERROR: could not read file $local: $!\n");
	}
    
	# Figure out the other necessary parameters.
	
	my $remote = $subtask->{remote};
	my $cmd = $subtask->{cmd};
	
	unless ( $remote || $cmd )
	{
	    my $label = $database || $local;
	    TaskErrorMessage("ERROR: no remote destination was specified for $label\n");
	    $rc = 10;
	    next SUBTASK;
	}
	
	# If the local filename has a .gz suffix make sure the remote name has one too. If not,
	# make sure the remote one does not either.
	
	elsif ( $remote )
	{
	    if ( $local =~ qr{ [.]gz $ }xs )
	    {
		$remote .= '.gz' unless $remote =~ qr{ [.]gz $ | [:/~] $ }xs;
	    }
	    
	    else
	    {
		$remote =~ s/[.]gz$//;
	    }
	}

	# Print out a message stating what we are doing.
	
	if ( $remote )
	{
	    print "Sending $local to $remote...\n";
	}
	
	elsif ( $cmd )
	{
	    print "Sending $local using $cmd...\n";

	    if ( $cmd =~ /%remote/ )
	    {
		TaskErrorMessage("ERROR: cannot execute '$cmd' because no remote site was specified.\n");
		$rc = 10;
		next SUBTASK;
	    }
	}
	
	# Now figure out the command to use to send this file. The default is 'scp', but that can
	# be overridden with the 'cmd' option.
	
	if ( $cmd )
	{
	    $cmd =~ s/%local/$local/;
	    $cmd =~ s/%remote/$remote/;
	    
	    print "  Executing: $cmd\n";
	}
	
	else
	{
	    $cmd = join(' ', 'scp', $local, $remote);
	}
	
	# If we are executing in test mode, skip the actual command.

	if ( $opt_test )
	{
	    print "Running in test mode: skipped.\n";
	    next SUBTASK;
	}
	
	# Otherwise, execute the command and record the result code if it is nonzero.
	
	SystemCommand($cmd);
	
	my $result = ResultCode();

	if ( $result )
	{
	    print "Failed with result code $result.\n";
	}
	
	else
	{
	    print "Complete.\n";
	}

	$rc = $result if $result;
    }
    
    my $elapsed = time - $start_time;
    my $min = int($elapsed/60);
    my $sec = $elapsed % 60;
    print "Elapsed time: $min minutes $sec seconds\n";
    
    return $rc;
}


$LDOC{test} = <<EndTest;

Usage:  {NAME} do test

Print out a simple message, and do nothing else.

EndTest

sub TestTask {
    
    my ($cmd, @args) = @_;

    foreach my $arg ( @args )
    {
	print "$arg\n";
    }
    
    print "Test task complete.\n";
    return 0;
}


$LDOC{'rotate-logs'} = <<EndRotate;

Usage:  {NAME} do rotate-logs(options)

Rotate and process the log files for the named service, or all log files for this
process. The default processing steps can be overridden by configuration options
if necessary. The basic action is to rename all of the log files generated by a
particular service, and then restart the service so that it generates new files
under the same names. These files are then processed according to the configured
options. Most of the log files are kept for a few weeks and then discarded, but
the main web logs are compressed and moved to the backup directory. This enables
us to keep track of usage statistics.

Options:

  all               Rotate and process the log files for all services. This is
                    the default.

  nginx             Rotate and process the nginx log files.

  api               Rotate and process the api log files. If the command being
                    run is 'pbdb', the log files for 'pbapi' are selected. If
                    it is 'macrostrat', the log files for 'msapi' are selected.
                    You can also specify either of those services explicitly.

  classic           Rotate and process the classic log files.

  default       Rotate and process the backup log file and the file that
                    records the actions of this task.

  force             Rotate and process log files even if they would not meet
                    the criteria for doing so.

  file=name...      Only process log files with the specified names. You can
                    specify more than one, separated by commas.

EndRotate

my ($LOG_DIR, $ROTATION_TIME, $ROTATION_WDAY, $ROTATION_MDAY, $ROTATION_MONTH, $ROTATION_YEAR);

sub RotateLogsTask {

    my ($cmd, @args) = @_;
    
    # The following two modules are needed for this task, but there is no reason to include them
    # when executing other tasks.
    
    require YAML::Tiny;
    require Scalar::Util;
    
    # Record the time at which this task was executed. These parameters will be used to determine
    # whether the specified periods have elapsed since the last rotation of each service and file.
    
    $ROTATION_TIME = time;

    my $dummy;
    
    ($dummy, $dummy, $dummy,
     $ROTATION_MDAY, $ROTATION_MONTH, $ROTATION_YEAR, $ROTATION_WDAY) = localtime($ROTATION_TIME);
    
    # Evaluate the arguments one by one.
    
    my (%selected, %selected_file, $opt_force, $opt_filename, $opt_gmt);
    
    foreach my $opt ( @args )
    {
	if ( $opt =~ qr{ ^ ( log | stdout ) (?: = (.*) )? $ }xs )
	{
	    # these options are handled by Command.pm, so are ignored here
	}
	
	elsif ( $opt =~ qr{ ^ ( all | nginx | api | pbapi | msapi | classic | default ) $ }xs )
	{
	    $selected{$1} = 1;
	}
	
	elsif ( $opt =~ qr{ ^ ( force | gmt ) $ }xs )
	{
	    $opt_force = 1 if $1 eq 'force';
	    $opt_gmt = 1 if $1 eq 'gmt';
	}
	
	elsif ( $opt =~ qr{ ^ ( file ) (?: = (.*) )? $ }xs )
	{
	    $opt_filename = $2 if $1 eq 'file';
	    die "ERROR: argument 'file' must have a nonempty value\n" unless $opt_filename;
	}
	
	else
	{
	    die "ERROR: unrecognized argument '$opt'\n";
	}
    }
    
    # If no services were specified on the command, the default is 'all'.
    
    unless ( %selected )
    {
	$selected{all} = 1;
    }
    
    # If 'api' was specified, then select either 'pbapi' or 'msapi' depending on which command is
    # being run.
    
    if ( $selected{api} )
    {
	$selected{pbapi} = 1 if $COMMAND eq 'pbdb';
	$selected{msapi} = 1 if $COMMAND eq 'macrostrat';
    }

    # If file=... was specified, then only the specified files will be rotated.
    
    if ( $opt_filename )
    {
	foreach my $f ( split /\s*,\s*/, $opt_filename )
	{
	    $selected_file{$f} = 1 if $f;
	}
    }
    
    # Construct a list of the built-in services we know about, then all keys from the
    # configuration setting 'service_rotation' that are not already on the list, in alphabetical
    # order. The pseudo-service 'default' is added at the end. Any log file not associated
    # with a service is rotated when that entry is processed. The service 'nginx' is rotated last
    # of all, because its logs require more extensive processing than the others. We want to leave
    # any possible trouble and length processing until all the rest of the task has been done.
    
    my @service_list;
    
    push @service_list, ('pbapi', 'classic') if $COMPONENT{paleobiodb}{path};
    push @service_list, ('msapi') if $COMPONENT{macrostrat}{path};
    
    my %builtin = map { $_ => 1 } @service_list;
    
    if ( ref $CONFIG{service_rotation} eq 'HASH' )
    {
	foreach my $k ( sort keys %{$CONFIG{service_rotation}} )
	{
	    push @service_list, $k unless $builtin{$k};
	}
    }
    
    push @service_list, 'default', 'nginx';
    
    # Construct a list of all the filenames we know how to rotate. These are the keys from the
    # configuration setting 'log_rotation'. Add them in alphabetical order, so that we have a
    # consistent order of subtasks across executions of this task.
    
    my @file_list;
    my @bad_list;
    
    foreach my $filename ( sort keys %{$CONFIG{log_rotation}} )
    {
	if ( $CONFIG{log_rotation}{$filename} && ref $CONFIG{log_rotation}{$filename} eq 'HASH' )
	{
	    push @file_list, $filename;
	    
	    # If all services are selected, then print an error message for any log file that has
	    # a non-empty 'service' attribute whose value does not correspond to an entry under
	    # the 'service_rotation' configuration setting. This probably indicates a
	    # typographical error which would keep that file from being rotated.
	    
	    my $service = $CONFIG{log_rotation}{$filename}{service};
	    
	    if ( $selected{all} && $service )
	    {
		unless ( $CONFIG{service_rotation}{$service} )
		{
		    push @bad_list, $filename;
		}
	    }
	}
    }
    
    # Print out a header, including a timestamp.
    
    my $now = $opt_gmt ? gmtime : localtime;
    my ($tz) = tzname;
    
    $tz = 'UTC' if $tz eq 'GMT' || $opt_gmt;
    
    print "------------------------------------------------------------\n";
    print "Initiating log rotation at $now $tz\n";
    print "Arguments: " . join(' ', @args) . "\n";

    # If we found bad service entries in the configuration file, print them out now.

    if ( @bad_list )
    {
	TaskErrorMessage("WARNING: the following files will not be rotated, because no corresponding\n");
	TaskErrorMessage("entries were found under the 'service_rotation' configuration setting.\n");
	
	foreach my $filename ( @bad_list )
	{
	    my $service = $CONFIG{log_rotation}{$filename}{service};
	    TaskErrorMessage("File $filename: service '$service' not found.\n");
	}
    }
    
    # The directory for log files is given by the configuration setting 'log_dir'. The current
    # directory during the execution of this task is $MAIN_PATH, so the pathname is relative to
    # that.
    
    $LOG_DIR = $CONFIG{log_dir} || 'logs';
    
    # If this directory does not exist, is not writeable, or is not a directory, abort execution of
    # this task.
    
    unless ( -r $LOG_DIR && -w $LOG_DIR && -d $LOG_DIR )
    {
	TaskErrorMessage("ERROR: Cannot write to directory $LOG_DIR: $!\n");
	TaskErrorMessage("Aborting log rotation.\n");
	return 4;
    }
    
    # If a 'status' file exists, read its contents. If an exception is thrown, abort execution of
    # this task. It is okay if the file does not exist or is empty; in that case, we proceed on
    # the assumption that this is the initial execution of this task.
    
    my $status_filename = "$LOG_DIR/status";
    my $status_root;
    
    my %status_file;
    my %status_new;
    
    if ( -e $status_filename )
    {
	eval {
	    $status_root = YAML::Tiny->read($status_filename);
	};
	
	if ( $@ )
	{
	    TaskErrorMessage("ERROR reading $status_filename:\n");
	    TaskErrorMessage($@);
	    TaskErrorMessage("Aborting log rotation.\n");
	    return 4;
	}
	
	if ( $status_root && Scalar::Util::reftype($status_root) eq 'ARRAY' &&
	     $status_root->[0] && Scalar::Util::reftype($status_root->[0]) eq 'HASH' )
	{
	    %status_file = %{$status_root->[0]};
	    %status_new = %status_file;
	}
    }
    
    unless ( %status_file )
    {
	print STDOUT "No status information was found in $status_filename.\n";
	print STDOUT "Proceeding on the assumption that this is the initial rotation.\n";
    }
    
    # Now run through the list of services we know about, and rotate the ones that were selected.
    
    my $rc = 0;

  SERVICE:
    foreach my $service ( @service_list )
    {
	# Skip services that weren't selected.
	
	next unless $selected{$service} || $selected{all};

	# Skip any service whose configuration entry is either 'disable' or has the subkey
	# 'disable' with a true value. Otherwise, warn about bad configuration entries but
	# continue anyway using defaults. Note that $service_params points to the global
	# configuration hash record, so any updates we make to it (i.e. filling in defaults) will
	# affect the rest of the current execution but will not be saved to disk. This is a fine
	# thing to do in this circumstance.
	
	my $service_params = $CONFIG{service_rotation}{$service};
	
	next if $service_params && $service_params eq 'disable';
	
	if ( $service_params && ref $service_params eq 'HASH' )
	{
	    next if $service_params->{disable};
	}
	
	else
	{
	    TaskErrorMessage("WARNING: no service_rotation configuration was found for '$service'.\n");
	    $service_params = { };
	}
	
	# If the option 'force' was specified, or if this is the 'default' entry, go straight to
	# checking the individual log files. Otherwise, rotate only if the interval specified by
	# the service parameters has elapsed.
	
	unless ( $opt_force || $service eq 'default' )
	{
	    # Warn about bad values, but continue anyway using defaults.
	    
	    my $period = $service_params->{period};
	    my $day = $service_params->{day};
	    my $default_set;
	    
	    if ( $period && $period !~ /^(daily|weekly|monthly|quarterly|never)$/i )
	    {
		TaskErrorMessage("WARNING for service_rotation configuration '$service': invalid period '$period'.\n");
		$service_params->{period} = undef;
		$service_params->{day} = undef;
	    }
	    
	    if ( $day && $day !~ /^\d+$/ )
	    {
		TaskErrorMessage("WARNING for service_rotation configuration '$service': invalid day '$day'.\n");
		$service_params->{day} = undef;
	    }
	    
	    # If the period is missing or was invalid, it defaults to 'weekly'.
	    
	    unless ( $service_params->{period} )
	    {
		$service_params->{period} = 'weekly';
		$default_set = 1;
	    }
	    
	    # Now check if this is the right date on which to rotate this service.
	    
	    my $trigger = CheckRotationPeriod($service_params, $status_new{$service});
	    next SERVICE unless $trigger;
	    
	    # If we get here, then we are about to rotate the files for this service. If the rotation
	    # period was set to a default value, print out a message about it now. That way, the
	    # message is only displayed on the occasion when the service is actually being
	    # rotated.
	    
	    if ( $default_set )
	    {
		my $period = $service_params->{period};
		my $day = $service_params->{day} || 1;
		print STDOUT "Defaulting period for '$service' to $period, day $day.\n";
	    }
	}
	
	# Now generate a list of log files that will be rotated with this service. This is done by
	# going through all of the files we know about and skipping all of those that are either
	# not associated with this service or are filtered out for various reasons.
	
	my @files;

      FILE:
	foreach my $filename ( @file_list )
	{
	    # If a "file=..." argument was given, ignore all files except those specified.
	    
	    next if %selected_file && ! $selected_file{$filename};
	    
	    # Ignore all files except those associated with this service. The 'default' entry gets
	    # all files that are not associated with any service.
	    
	    if ( my $s = $CONFIG{log_rotation}{$filename}{service} )
	    {
		next FILE unless $service eq $s;
	    }
	    
	    else
	    {
		next FILE unless $service eq 'default';
	    }
	    
	    # If the option 'force' was specified, then include every file without checking.
	    
	    if ( $opt_force )
	    {
		push @files, $filename;
	    }
	    
	    # Otherwise, check the individual files.
	    
	    else
	    {
		my $log_params = $CONFIG{log_rotation}{$filename};
		my $file_period = $log_params->{period};
		my $service_period = $service_params->{period};
		my $time_trigger = 1;
		my $size_trigger;
		
		# For services other than 'default', we start with $time_trigger true. If the
		# service rotation has been triggered, then we want to rotate all associated files
		# except those with rules specifyig otherwise. But for 'default', we start with
		# $time_trigger false. We only want to rotate these files if their own attributes
		# trigger it. The default time period for these files is 'never'.
		
		if ( $service eq 'default' )
		{
		    $time_trigger = 0;
		    $service_period = 'never';
		}
		
		# If the file's rotation period differs from the service rotation period, check it
		# separately. This may clear the time trigger. Ignore rotation days for
		# service-associated files, but respect them for files not associated with any service.
		
		if ( $file_period && $file_period ne $service_period )
		{
		    if ( $file_period !~ /^(daily|weekly|monthly|quarterly|never)$/i )
		    {
			TaskErrorMessage("WARNING for log_rotation configuration '$filename': " .
					 "invalid period '$file_period'.\n");
			TaskErrorMessage("Defaulting to service period ($service_period).\n");
		    }
		    
		    else
		    {
			delete $log_params->{day} unless $service eq 'default';
			$time_trigger = CheckRotationPeriod($log_params, $status_new{$filename});
		    }
		}
		
		# If a file size limit was set, check to see if the file's size exceeds the
		# limit. If specified as 'min_size', the file will be included only if the
		# specified time interval has also elapsed. Otherwise, the file will be included
		# whenever it is found to have exceeded the size limit.
		
		my $size_limit = $log_params->{min_size} || $log_params->{size};
		my $min_size = $log_params->{min_size};
		
		if ( $size_limit )
		{
		    if ( $size_limit !~ /^(\d+)([bkmg]?)$/i )
		    {
			TaskErrorMessage("WARNING for log_rotation configuration '$filename': " .
					 "invalid size limit '$size_limit' ignored.\n");
		    }
		    
		    else
		    {
			my $magnitude = $1;
			my $unit = $2 || 'B';
			my $dir = $log_params->{dir} || $service_params->{dir};
			my $full_filename = $dir ? "$dir/$filename" : $filename;
			$size_trigger = CheckRotationSize($full_filename, $magnitude, uc($unit));
		    }
		}
		
		# Include this file if the time interval has elapsed and there is no min_size limit.
		
		if ( $time_trigger && ! $min_size )
		{
		    push @files, $filename;
		}
		
		# Alternatively, include this file if it exceeds a size limit, and either it was a
		# hard limit (not a min_size limit) or the time interval has also elapsed.
		
		elsif ( $size_trigger && ( ! $min_size || $time_trigger ) )
		{
		    push @files, $filename;
		}
	    }
	}
	
	# If there are no files and there is no restart action defined for this service, we can
	# skip it completely. If this is a service other than 'default', and there was not an
	# explicit file= argument, then print out a message stating that no files will be rotated.
	
	unless ( @files )
	{
	    next SERVICE if $service eq 'default';
	    
	    unless ( %selected_file )
	    {
		print STDOUT "There are no logs to rotate for service '$service'.\n";
	    }
	    
	    next SERVICE if $service_params->{restart} && $service_params->{restart} eq 'none';
	    next SERVICE if $service_params->{container_restart} && $service_params->{container_restart} eq 'none';
	}
	
	# Otherwise, indicate that we are starting a rotation subtask.
	
	if ( $service eq 'default' )
	{
	    print STDOUT "Rotating miscellaneous logs:\n";
	}
	
	else
	{
	    print STDOUT "Rotating logs for service $service:\n";
	}
	
	# Call RotateService to restart the service and rotate all of the files associated with
	# it. The call is made inside an eval block so that an exception thrown by one call will
	# still allow the others to be completed. If any call returns a nonzero result, the last
	# such result will be returned as the result of the entire task.
	
	my $result;
	
	eval {
	    $result = RotateService($service, $service_params, \@files, \%status_new);
	};
	
	$rc = $result if $result;
	
	# If an exception is thrown, treat this as a result code of 10 and print out the error
	# message both to the log file (if any) and to STDERR.
	
	if ( $@ )
	{
	    TaskErrorMessage($@);
	    $rc = 10;
	}
    }
    
    # Now total up how many files were actually rotated, based on the values in %status_new.
    
    my $files_rotated = 0;
    
    foreach my $key ( keys %status_new )
    {
	$files_rotated++ if $status_new{$key} ne $status_file{$key};
    }
    
    # If we have done at least one rotation, update the status file and print out an elapsed time.
    
    if ( $files_rotated )
    {
	my $elapsed = time - $ROTATION_TIME;
	my $min = int($elapsed/60);
	my $sec = $elapsed % 60;
	
	print "Elapsed time: $min minutes $sec seconds\n";
	
	my $status_out = YAML::Tiny->new( \%status_new );
	$status_out->write($status_filename);
    }
    
    # Otherwise, note the fact that we didn't do anything.
    
    else
    {
	print "No files or services were rotated.\n";
    }
    
    # Return a nonzero result code if any of the subtasks did, zero otherwise.
    
    return $rc;
}


# CheckRotationPeriod ( params, status )
# 
# Return true if the parameters (for a service or an individual file) given in $params together
# with the last rotation status from $status indicate that a rotation should be done now.
# 
# The time at which this task was run has already been stored by the calling routine in
# $ROTATION_TIME, together with the computed time components in $ROTATION_WDAY, etc. This task is
# designed to be run daily, so the smallest allowed rotation period is 'daily'.

sub CheckRotationPeriod {
    
    my ($name, $params, $status, $service_status) = @_;
    
    # If the rotation period is 'never' or there is no period at all, then we can return false
    # right now.
    
    return if ! $params->{period} || $params->{period} eq 'never';
    
    # If we have the date of the last rotation from the status file, extract it now. But if the
    # timestamp is not a number that exceeds a value of time() during the development of this
    # code, print out an error message and leave the time components undefined.
    
    my ($last_rotation, $dummy, $wday, $mday, $month, $year);
    
    if ( $status->{timestamp} && $status->{timestamp} > 1596488501 )
    {
	($last_rotation) = $status->{timestamp};
	($dummy, $dummy, $dummy, $mday, $month, $year, $wday) = localtime($status->{timestamp});
    }
    
    elsif ( $status->{timestamp} )
    {
	TaskErrorMessage("Bad timestamp '$status->{timestamp}' for '$name'.\n");
    }
    
    # Now check the specified period and optional day number.
    
    my $period = $params->{period};
    
    # If the period is 'daily', then the period is irrelevant. Rotation will be done unless there
    # is a valid previous timestamp that indicates a rotation was already done today.
    
    if ( $period eq 'daily' )
    {
	return ! (defined $last_rotation &&
		  $mday == $ROTATION_MDAY &&
		  $month == $ROTATION_MONTH &&
		  $year == $ROTATION_YEAR);
    }
    
    # The period 'weekly' is the default, so will be frequently encountered. Rotate unless there
    # is a valid previous timestamp that indicates a rotation already occurred this week. But if a
    # specific day of the week is specified, suppress rotation until the current day of week is at
    # least that number.
    
    elsif ( $period eq 'weekly' )
    {
	# If a day of week was specified, suppress rotation until we have reached that point in
	# the week. Note that use of the 'day' parameter may cause improper functioning if this
	# task is not executed daily!!!
	
	if ( $params->{day} && $params->{day} > 0 )
	{
	    return unless $ROTATION_WDAY >= $params->{day};
	}
	
	# Rotate unless we know for certain that a previous rotation already occurred this
	# week. Any rotation that occurred more than 6.75 days ago is not "this week".
	
	my $days = 86400;
	
	return ! (defined $wday && $wday <= $ROTATION_WDAY && $ROTATION_TIME - $last_rotation < 6.75 * $days);
    }
    
    # If the period is 'monthly', rotate unless we know that the previous rotation occurred this
    # month. If a specific day of the month was specified, rotation will be suppressed until the
    # current day of month is at least that number.
    
    elsif ( $period eq 'monthly' )
    {
	# If a day of month was specified, suppress rotation until we have reached that point in
	# the month. We have to add one because the month numbers returned by 'localtime' start
	# with 0.
	
	if ( $params->{day} && $params->{day} > 0 )
	{
	    return unless $ROTATION_MDAY + 1 >= $params->{day};
	}
	
	# Rotate unless we know that the last rotation occurred this month.
	
	return ! (defined $mday &&
		  $mday <= $ROTATION_MDAY &&
		  $month == $ROTATION_MONTH &&
		  $year == $ROTATION_YEAR);
    }

    # If the period is 'quarterly', rotate unless we know that the previous rotation occurred this
    # quarter. The 'day' parameter is only respected if its value is <= 30, because I cannot see
    # any reason to waste time implementing it for larger values. This will allow a small offset
    # within the first month if desired.
    
    elsif ( $period eq 'quarterly' )
    {
	# If a day of quarter is specified with a value <= 30, suppress rotation until we have
	# reached that point in the quarter.

	if ( $params->{day} && $params->{day} >= 0 && $params->{day} <= 30 )
	{
	    return unless $ROTATION_MONTH % 4 == 0 && $ROTATION_MDAY >= $params->{day};
	}
	
	# Rotate unless we know that the last rotation occurred this quarter.
	
	return ! (defined $month &&
		  int($month/4) == int($ROTATION_MONTH/4) &&
		  $year == $ROTATION_YEAR);
    }

    # If for whatever reason we get some other value, return false.

    return;
}


# CheckRotationSize ( full_filename, size_limit, units )
#
# Return true if the specified file exceeds the specified limit, false otherwise.

sub CheckRotationSize {
    
    my ($full_filename, $size_limit, $unit) = @_;

    my $byte_size = $unit eq 'G' ? $size_limit * 1073741824
	          : $unit eq 'M' ? $size_limit * 1048576
		  : $unit eq 'K' ? $size_limit * 1024
		                 : $size_limit;

    return -s $full_filename >= $byte_size;
}


# RotateService ( service, parameters, files, status )
# 
# Rotate all of the specified log files, and then restart the service if there is a restart action
# specified for it. If any of the files have post-processing actions specified for them, proceed
# to execute those actions if the restart succeeded.

sub RotateService {
    
    my ($service, $service_params, $file_list, $status) = @_;
    
    my $error_count;
    
    my @action_list;
    my %indicator_file;
    
    # Rotate the associated files one by one. If additional processing actions are specified for a
    # file, add it to @action_list to be handled after the service restarts.
    
   FILE:
    foreach my $filename ( @$file_list )
    {
	my $log_params = $CONFIG{log_rotation}{$filename};

	# Determine the full name of the file to be rotated.
	
	my $dir = $log_params->{dir} || $service_params->{dir};
	
	my $full_filename = $dir ? "$dir/$filename" : $filename;
	
	# Determine if it will need post-processing.
	
	my $needs_processing = $log_params->{append} || $log_params->{process} || $log_params->{compress};
	
	# If 'keep' is specified to be 0, then the file is simply unlinked.
	
	if ( defined $log_params->{keep} && $log_params->{keep} eq '0' )
	{
	    # Unlinking a file is incompatible with processing actions, so print out an error
	    # message if the configuration setting includes any of those.
	    
	    if ( $needs_processing )
	    {
		TaskErrorMessage("WARNING for '$filename': $full_filename was not unlinked.\n");
		TaskErrorMessage("File attribute 'append' is incompatible with keep=0\n") if $log_params->{append};
		TaskErrorMessage("File attribute 'process' is incompatible with keep=0\n") if $log_params->{process};
		TaskErrorMessage("File attribute 'compress' is incompatible with keep=0\n") if $log_params->{compress}; 
	    }
	    
	    # Otherwise, if the file exists then remove it.
	    
	    elsif ( -e $full_filename )
	    {
		my $result = RotateRemove($full_filename);

		# If the remove succeeds, update the status. Otherwise, leave the status as it was
		# and increment the error count.
		
		if ( $result )
		{
		    $status->{$filename} = { status => 'removed', timestamp => $ROTATION_TIME };
		}
		
		else
		{
		    $error_count++;
		}
	    }
	    
	    # If the file doesn't exist, note that fact.
	    
	    else
	    {
		$status->{$filename} = { status => 'notfound', timestamp => $ROTATION_TIME };
	    }

	    next FILE;
	}
	
	# Otherwise, 'keep' defaults to 1 unless a higher value is specified. Files with a
	# 'keep' of 1 or greater are only rotated if they exist and are non-empty.
	
	elsif ( -e $full_filename && -s $full_filename )
	{
	    # If there are post-processing actions still pending for the previous rotation of this
	    # file, try to do them before this new rotation. Clear the 'actions_pending' flag
	    # regardless of whether or not these actions succeed.
	    
	    if ( $status->{$filename}{actions_pending} )
	    {
		delete $status->{$filename}{actions_pending};
		RotatePostProcess($full_filename, 1, $log_params);
	    }
	    
	    # Now rotate the file.
	    
	    my $keep_number = $log_params->{keep} || 1;
	    my $result = RotateKeep($full_filename, $keep_number);
	    
	    # If the rotation succeeded, update the file's status. If post-processing actions are
	    # defined for this file, add it to the action list.
	    
	    if ( $result )
	    {
		$status->{$filename} = { status => 'rotated', timestamp => $ROTATION_TIME };

		push @action_list, $filename if $needs_processing;
		
		# If this is the 'indicator file' for its service, flag it as such.
		
		$indicator_file{$service} = $full_filename if $log_params->{indicator};
	    }
	    
	    # If the rotation failed, increment the error count. We ignore any post-processing
	    # actions, since the file was not moved and all the data remains where it was.
	    
	    else
	    {
		$error_count++;
	    }

	    next FILE;
	}
	
	# A non-existent or empty file may indicate a serious problem.
	
	else
	{
	    # If there are actions pending for this file, and no new file to rotate, add the file
	    # to the action list and go on to the next one. We will try again to restart the service,
	    # and if that works then the data can be post-processed.
	    
	    if ( $status->{$filename}{actions_pending} )
	    {
		push @action_list, $filename;
		next FILE;
	    }
	    
	    # If the file is otherwise nonexistent or empty, print out a warning message unless
	    # the empty_ok setting is true. Unless indicated by that setting, all of these files
	    # SHOULD have data in them. It is important to let the administrator know if one or
	    # more does not, because that probably an indication that something important has gone
	    # wrong. But do not increment the error count, because we just want to warn about a
	    # file that we expect to have data in it rather than recording an error condition.
	    
	    unless ( $log_params->{empty_ok} )
	    {
		my $message = -e $full_filename ? 'is empty' : 'does not exist';
		TaskErrorMessage("WARNING: file '$full_filename' was not rotated because it $message.\n");
	    }

	    my $new_status = -e $full_filename ? 'empty' : 'notfound';
	    
	    $status->{$filename} = { status => $new_status, timestamp => $ROTATION_TIME };
	    
	    next FILE;
	}
    }
    
    # Now restart the service, if that is appropriate.
    
    my $can_process;
    
    # If an explicit value of 'none' was given for either the 'restart' setting or the
    # 'container_restart' setting, do not restart this service at all. The pseudo-service
    # 'default' does not have any associated container, so it does not get restarted either.
    
    if ( $service eq 'default' ||
	 $service_params->{restart} && $service_params->{restart} eq 'none' ||
	 $service_params->{container_restart} && $service_params->{container_restart} eq 'none' )
    {
	$can_process = 1;
	$status->{$service} = { status => 'none', timestamp => $ROTATION_TIME };
    }
    
    # If a specific restart command was given, execute it directly without regard to any
    # container. This can be used for services that execute outside of docker, for example.
    
    elsif ( $service_params->{restart} )
    {
	my $result = SystemCommand($service_params->{restart});
	
	# If the command succeeds, assume that we can safely process the log files. If it fails,
	# log file processing will have to wait for the next execution of this task.
	
	if ( $result )
	{
	    $can_process = 1;
	    $status->{$service} = { status => 'restarted', timestamp => $ROTATION_TIME };
	    print STDOUT "Restarted service $service.\n";
	}
	
	else
	{
	    my $rc = ResultCode();
	    TaskErrorMessage("FAILED to restart service $service, result code = $rc\n");
	    TaskErrorMessage("Command was '$service_params->{restart}'\n");
	    $error_count++;
	}
    }
    
    # Otherwise, the service container needs to be checked and in most cases restarted.
    
    else
    {
	# Start by determining the container name.
	
	my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
	my $container_name = join('_', $base_name, $service, "1");
	
	# Before we try to restart the container, check to see if it is running.
	
	my $container_up;
	
	my @lines = CaptureCommand('docker', 'ps', '--filter', "name=$container_name",
				   '--format', '{{.Status}}::{{.Names}}');
	
	foreach my $line ( @lines )
	{
	    my ($status, $name) = split /::/, $line;
	    
	    if ( $name !~ /_run_\d$/ && $status =~ /^Up/ )
	    {
		$container_up = 1;
	    }
	}
	
	# If the service is up, then try to restart it.
	
	if ( $container_up )
	{
	    my $result;
	    my $command;
	    
	    # If a command is given under the setting 'container_restart', execute this command in
	    # the service container. If it succeeds, assume that we can process the log files.
	    
	    if ( $service_params->{container_restart} )
	    {
		$result =  SystemCommand('docker', 'exec', $container_name, 'sh', '-c',
					 $service_params->{container_restart});
		$command = "docker exec $container_name sh -c \"$service_params->{container_restart}\"";
	    }
	    
	    # Otherwise, just execute 'docker restart' on the container. This will probably be
	    # sufficient in most or all cases.
	    
	    else
	    {
		$result = SystemCommand('docker', 'restart', $container_name);
		$command = "docker restart $container_name";
	    }
	    
	    # If the command succeeds, then the service has been restarted and we can process the
	    # logs.
	    
	    if ( $result )
	    {
		$can_process = 1;
		$status->{$service} = { status => 'restarted', timestamp => $ROTATION_TIME };
		print STDOUT "Restarted service $service.\n";
	    }

	    # If a new version of the indicator log file has been re-created after rotation and has only a
	    # small amount of data in it, that indicates that the service has been restarted even
	    # if the result code was bad. So we can still process the logs.
	    
	    elsif ( $indicator_file{$service} && -e $indicator_file{$service} &&
		    -s $indicator_file{$service} < 4096 )
	    {
		$can_process = 1;
		$status->{$service} = { status => 'restarted', timestamp => $ROTATION_TIME };
		my $rc = ResultCode();
		print STDOUT "Restarted service $service. Inferred from indicator file, result code = $rc\n";
	    }
	    
	    # Otherwise, log processing will have to wait until the next time this
	    # task is executed.
	    
	    else
	    {
		my $rc = ResultCode();
		TaskErrorMessage("FAILED to restart service $service, result code = $rc\n");
		TaskErrorMessage("Command was '$command'\n");
		$error_count++;
	    }
	}
	
	# If the service is not up, then we can go ahead and carry out any processing actions on
	# the rotated log files because any processes that had been writing to them have
	# terminated. But we still print an error message, because we want to let the
	# administrator know that something is wrong.
	
	else
	{
	    $can_process = 1;
	    $status->{$service} = { status => 'down', timestamp => $ROTATION_TIME };
	    TaskErrorMessage("SERVICE DOWN: $service\n");
	    $error_count++;
	}
    }
    
    # We now finish up this subroutine by going through the action list. For every pending action,
    # if $can_process is true then do it. If $can_process is false, print an error message and set
    # the 'actions_pending' flag on that file.
    
    foreach my $filename ( @action_list )
    {
	my $log_params = $CONFIG{log_rotation}{$filename};
	
	my $dir = $log_params->{dir} || $service_params->{dir};
	
	my $full_filename = $dir ? "$dir/$filename" : $filename;
	
	my $success = RotatePostProcess($full_filename, $can_process, $log_params);
	
	unless ( $can_process )
	{
	    $status->{$filename}{actions_pending} = 1;
	    $error_count++;
	}
	
	elsif ( $success )
	{
	    $status->{$filename}{status} = 'processed';
	}
	
	else
	{
	    $error_count++;
	}
    }
    
    # If errors occurred, return a nonzero result code. Otherwise return 0.

    if ( $error_count )
    {
	return 2;
    }

    else
    {
	return 0;
    }
}


# RotateRemove ( full_filename )
#
# Unlink the specified file. Return true if this succeeds, generate an error message and return
# false otherwise.

sub RotateRemove {

    my ($full_filename) = @_;
    
    my $result = unlink $full_filename;

    unless ( $result )
    {
	TaskErrorMessage("ERROR: failed to unlink $full_filename: $!\n");
    }

    return $result;
}


# RotateKeep ( full_filename, keep_number )
#
# Rename the file full_filename to full_filename.1, full_filename.1 to full_filename.2, etc. until
# the keep_number is reached. Return true if this succeeds, generate an error message and return
# false otherwise.

sub RotateKeep {
    
    my ($full_filename, $keep_number) = @_;

    # We need to do the renaming in reverse order, so that none of the earlier files get
    # overwritten. Silently skip any file that does not exist, because an earlier renaming may have
    # been interrupted. However, check both xxx.1 and xxx.1.gz.
    
    my $last = $keep_number + 0;
    
    if ( $last > 1 )
    {
	for ( my $i = $last - 1; $i > 0; $i-- )
	{
	    my $next = $i + 1;
	    
	    if ( -e "$full_filename.$i" )
	    {
		my $result = rename "$full_filename.$i", "$full_filename.$next";

		unless ( $result )
		{
		    TaskErrorMessage("ERROR: failed to rename $full_filename.$i to $full_filename.$next: $!\n");
		    return;
		}
	    }

	    if ( -e "$full_filename.$1.gz" )
	    {
		my $result = rename "$full_filename.$i.gz", "$full_filename.$next.gz";
		
		unless ( $result )
		{
		    TaskErrorMessage("ERROR: failed to rename $full_filename.$i.gz to $full_filename.$next.gz: $!\n");
		    return;
		}
	    }
	}
    }

    my $result = rename $full_filename, "$full_filename.1";

    unless ( $result )
    {
	TaskErrorMessage("ERROR: failed to rename $full_filename to $full_filename.1: $!\n");
    }
    
    return $result;
}


# RotatePostProcess ( full_filename, process, log_params, status )
# 
# If $process is true, then do all post-processing actions specified for this file. Return true if
# they all succeed, false if any of them fail. If $process is false, print out error messages
# for each action indicating that the action is postponed.

sub RotatePostProcess {

    my ($full_filename, $can_process, $log_params, $status) = @_;
    
    my $success = $can_process ? 1 : undef;
    
    # The file to process is the first rotated file, not the original. The original is presumably
    # by this point being filled up with new data since the service has already been restarted.
    
    my $rotated_filename = "$full_filename.1";
    
    # Check to make sure that the rotated file is actually readable. Many of the container
    # processes run as root, and it is possible that the log file is not readable by the userid
    # under which this task is being run. In that case, print out an error message and do not
    # attempt to post-process the file.
    
    unless ( -r $rotated_filename )
    {
	TaskErrorMessage("FAILED to process $rotated_filename: $!\n");
	return;
    }
    
    # If an 'append' action is specified, do that first.
    
    if ( $log_params->{append} )
    {
	my $destination = RotateSubstituteString($log_params->{append});
	
	if ( $can_process )
	{
	    my $result = RotateAppendFile($rotated_filename, $destination);
	    $success = undef unless $result;
	}
 	
	else
	{
	    TaskErrorMessage("POSTPONED appending $rotated_filename => $destination\n");
	}
   }
    
    # If a 'process' action is specified, do that next.
    
    if ( $log_params->{process} )
    {
	my $command = RotateSubstituteString($log_params->{process});

	if ( $can_process )
	{
	    my $result = RotateProcessFile($full_filename, $command);
	    $success = undef unless $result;
	}
 
	else
	{
	    TaskErrorMessage("POSTPONED processing $full_filename => $command\n");
	}
    }
    
    # If a 'compress' action is specified, do that last.
    
    if ( $log_params->{compress} )
    {
	if ( $can_process )
	{
	    my $result = RotateCompressFile($full_filename);
	    $success = undef unless $result;
	}
	
	else
	{
	    TaskErrorMessage("POSTPONED compressing $full_filename\n");
	}
    }
    
    return $success;
}


# RotateAppendFile ( source, destination )
#
# Append the data from the file $source to $destination. Return true if this succeeds. Otherwise,
# print out an error message and return false. We explicity check that the file is readable first,
# because if it is not we can include a precise message in the logs.

sub RotateAppendFile {
    
    my ($source, $destination) = @_;
    
    my $result = SystemCommand('cat', $source, '>>', $destination);

    if ( $result )
    {
	print STDOUT "Appended $source => $destination\n";
    }
    
    else
    {
	print STDOUT "ERROR: append failed for $source => $destination\n";
    }

    return $result;
}


# RotateProcessFile ( source, command )
# 
# Direct the data from the file $source to the command $command. Return true if this
# succeeds. Otherwise, print out an error message and return false. We explicity check that the
# file is readable first, because if it is not we can include a precise message in the logs.

sub RotateProcessFile {
    
    my ($source, $command) = @_;
    
    my $result = SystemCommand("cat $source | $command");
    
    if ( $result )
    {
	print STDOUT "Processed $source => $command\n";
    }
    
    else
    {
	print STDOUT "ERROR: processing failed for $source => $command\n";
    }

    return $result;
}


# RotateCompressFile ( source )
#
# Compress the specified file using 'gzip'. Return true if this succeeds. Otherwise, print out an
# error message and return false. We explicity check that the file is readable first, because if
# it is not we can include a precise message in the logs.

sub RotateCompressFile {
    
    my ($source) = @_;
    
    my $result = SystemCommand("gzip $source");

    if ( $result )
    {
	print STDOUT "Compressed $source => $source.gz\n";
    }
    
    else
    {
	print STDOUT "ERROR: compress failed for $source\n";
    }
}


# RotateSubstituteString ( string )
#
# If the specified string contains either 'DATE', 'YYYY-MM', or 'YYYY-MM-DD', substitute the
# current date components.

sub RotateSubstituteString {

    my ($string) = @_;
    
    return $string unless $string =~ /DATE|YYYY|MM|DD/;
    
    my $year = $ROTATION_YEAR > 1900 ? $ROTATION_YEAR : $ROTATION_YEAR + 1900;
    my $month = sprintf("%02d", $ROTATION_MONTH + 1);
    my $day = sprintf("%02d", $ROTATION_MDAY);
    
    $string =~ s/DATE/YYYY-MM-DD/g;
    $string =~ s/YYYY/$year/g;
    $string =~ s/MM/$month/g;
    $string =~ s/DD/$day/g;
    
    return $string;
}


# HelpString ( command )
#
# Return the help string for the specified command.

sub HelpString {

    my ($cmd) = @_;

    if ( $LDOC{$cmd} )
    {
	return $LDOC{$cmd};
    }

    else
    {
	return "\nNo documentation is available for the subcommand '$cmd'\n\n";
    }
}


1;
