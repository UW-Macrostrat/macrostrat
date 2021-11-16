#
# Paleobiology Database control command
#
# This module implements the guts of the paleobiodb control command.
# 
# Author: Michael McClennen
# Created: 2019-12-13


use strict;

package PMCmd::Command;

use parent 'Exporter';

use PMCmd::Config qw(%CONFIG $MAIN_PATH $MAIN_NAME $DEBUG $COMMAND ReadLocalConfig);
use PMCmd::System qw(GetComposeServices GetServiceStatus GetContainerID
		       ExecDockerCompose SystemDockerCompose CaptureDockerCompose
		       SystemCommand CaptureCommand ExecCommand ResultCode);

use Getopt::Long;

our (@EXPORT_OK) = qw(DisplayStatus PrintOutputList TaskErrorMessage TaskConfigSelect TaskConfigAll);

our (%LDOC, %EDOC);


# StatusCmd ( service... )
# 
# This routine implements the subcommand 'status'. If no service names are specified, the status
# of all services is given. More than one name can be specified, separated by commas or whitespace.

$LDOC{status} = <<ENDStatus;

Usage:  {NAME} status [OPTIONS] [SERVICE...]

Display the status of all containers if no argument is given or if the argument
'all' is given. If one or more arguments are given, only display containers
associated with corresponding service(s). Service names can be separated by
spaces or commas.

Options:
  --summary             Display a single line of text summarizing the status
                          of the services, disregarding other containers.
  --no-color            Display plain text, without any control characters to
                          set colors.
  -x, --extended        Also display the memory footprint of each container
                          and the command run in it.

ENDStatus

sub StatusCmd {
    
    my $cmd = shift @ARGV;
    
    # First, check for additional options.
    
    my ($opt_summary, $opt_extended, $opt_nocolor, $opt_all);
    
    GetOptions( "summary|s" => \$opt_summary,
		"extended|x" => \$opt_extended,
		"no-color" => \$opt_nocolor,
	        "all" => \$opt_all);
    
    # Then display the status of the services indicated by the remainder of @ARGV.
    
    my $options = { summary => $opt_summary,
		    extended => $opt_extended,
		    nocolor => $opt_nocolor };
    
    my @list = grep { $_ =~ /[a-z]/i } map { split /\s*,\s*/, $_ } @ARGV;
    
    DisplayStatus($options, @list);
}


# DisplayStatus ( [options], service... )
#
# Display the status of one or more services. The first argument may optionally be a hash of
# option values.

sub DisplayStatus {

    my $options = ref $_[0] eq 'HASH' ? shift @_ : { };
    
    my (@select_services) = @_;
    
    # First, check the argument list against the known list of services. Error messages will be
    # printed for each argument that is not an actual service. If no valid service names were
    # given, return without displaying anything.
    
    my $show_all = @select_services == 0 || $select_services[0] eq 'all';
    
    my @service_list = GetComposeServices(@select_services);
    exit 2 unless @service_list;
    
    # Generate a filter for the output of docker ps.
    
    my %select = map { $_ => 1 } @service_list;
    
    # Determine the info we will need to fetch.

    my $format = '{{.Names}}::{{.Label "com.docker.compose.service"}}::{{.Status}}::{{.Size}}::{{.Command}}';
    
    # Then get a list of process status lines from docker. The --all option gives us information
    # about all containers, not just running ones. The --no-trunc option gives us full information
    # about the command and size with no truncation.
    
    my @lines = CaptureCommand('docker', 'ps', '--all', '--no-trunc', '--format', $format);
    
    chomp @lines;
    
    my (%found, @service_entries, @other_entries);
    
    # Now go through the lines and collect up all that match the selection.
    
    foreach my $line ( @lines )
    {
	my (@params) = split /::/, $line;
	my ($name, $service, $status) = @params;
	
	# Service containers can be recognized by the format of their name. Select just the
	# services indicated by the arguments. We keep track of the services that we find listings
	# for, so that we can include a 'No container' line for any selected services that do not
	# appear in the list.
	
	if ( $service && $name =~ / _${service}_1 $ /xs )
	{
	    $found{$service} = 1;
	    $params[0] = "service $service:";
	    push @service_entries, \@params if $select{$service};
	}
	
	# If we are showing all services instead of just a selection, list all other containers as
	# well. Those go on a separate list, which will get displayed at the end.
	
	elsif ( $show_all && ! $options->{summary} )
	{
	    push @other_entries, \@params;
	}
    }
    
    # If there are any services that we did not find containers for, add dummy listings.
    
    foreach my $s ( @service_list)
    {
	if ( $select{$s} && ! $found{$s} )
	{
	    push @service_entries, ["service $s:", $s, 'No container'];
	}
    }
    
    # Now if the summary option was given, we report a single line indicating whether all services
    # are up, some are down, or all are down. All of the other entries are ignored.
    
    if ( $options->{summary} )
    {
	my (@up_list, @down_list);
	
	# Check whether each listed service container is up. Any that are paused, stopped, or
	# otherwise not fully running are considered to be down.
	
	foreach my $params ( @service_entries )
	{
	    if ( $params->[2] =~ / ^ up (?! .* paused) /xsi )
	    {
		push @up_list, $params->[1];
	    }
	    
	    else
	    {
		push @down_list, $params->[1];
	    }
	}
	
	# Now print out a single summary line.
	
	if ( @up_list && ! @down_list )
	{
	    print "ALL UP\n";
	}
	
	elsif ( @up_list )
	{
	    my $down = join(' ', @down_list);
	    print "SOME DOWN ($down)\n";
	}
	
	else
	{
	    print "ALL DOWN\n";
	}

	return;
    }
    
    # Otherwise, we are going to be printing out one status line for each entry. If $show_all is
    # true, then append entries for non-service containers to the display list. Add a spacer
    # element to separate the two lists visually.
    
    my @display = @service_entries;
    push @display, '-------------------------------------', @other_entries if $show_all && @other_entries;
    
    # Go through the display list and compute a maximum width for each column.
    
    my @column_max;
    
    foreach my $params ( @display )
    {
	next unless ref $params;
	
	# compute a maximum width for each column in the result. This will be used
	# below to format the displayed output.
	
	foreach my $i (0..$#$params)
	{
	    if ( ! $column_max[$i] || length($params->[$i]) > $column_max[$i] )
	    {
		$column_max[$i] = length($params->[$i]);
	    }
	}
    }
    
    # Then format and print out the display list using the maximum widths computed above.
    
    my $col0 = $column_max[0] + 1;
    my $col2 = $column_max[2];
    my $col3 = $column_max[3];
    my $col4 = $column_max[4];
    
    my $pattern;
    
    foreach my $s ( @display )
    {
	unless ( ref $s )
	{
	    print "$s\n";
	    next;
	}
	
	my $on = '';
	my $off = '';
	
	unless ( $options->{nocolor} )
	{
	    if ( $s->[2] =~ / ^ up (?! .* paused) /xsi )
	    {
		$on = "\033[0;32m";
		$off = "\033[0m";
	    }
	    
	    else
	    {
		$on = "\033[0;31m";
		$off = "\033[0m";
	    }
	}
	
	if ( $options->{extended} )
	{
	    $pattern = "  %-${col0}s \%s%-${col2}s\%s     %-${col3}s     \%s\n";
	    print STDOUT sprintf($pattern, $s->[0], $on, $s->[2], $off, $s->[3], $s->[4]);
	}
	
	elsif ( $s->[0] =~ /^service / )
	{
	    $pattern = "  %-${col0}s \%s%-${col2}s\%s     \%s\n";
	    print STDOUT sprintf($pattern, $s->[0], $on, $s->[2], $off);
	}
	
	else
	{
	    my $cmd = $s->[4];
	    my $service = $s->[1];
	    $cmd = "($service) $cmd" if $service && $s->[0] !~ /_${service}_/;
	    $pattern = "  %-${col0}s \%s%-${col2}s\%s     \%s\n";
	    print STDOUT sprintf($pattern, $s->[0], $on, $s->[2], $off, $cmd);
	}
    }
}


# ListServicesCmd ( )
#
# This routine implements the subcommand 'services'.

$LDOC{services} = <<ENDServices;

Usage:  {NAME} services

Display a list of service names. These can be used as arguments to subsequent
invocations of this command.

ENDServices

sub ListServicesCmd {

    foreach my $s ( GetComposeServices() )
    {
	print "$s\n";
    }
}


# ControlCmd ( )
#
# This routine implements the subcommands 'up', 'down', 'start', 'stop', 'restart',
# 'kill', 'pause', 'unpause', 'logs'.

$EDOC{up} = "docker-compose help up";
$LDOC{up} = <<ENDUp;

Usage:  {NAME} up [OPTIONS] [SERVICE...]

Bring up the specified service, or all of them if no service name is specified.
You can use any of the options available for the 'docker-compose up' command.
The -d option is included automatically, so the service(s) are always started
in detached mode. The --no-build option is also included automatically, because
container images should be built using the {NAME} command rather than by
docker-compose. If you are bringing up a single service, the last 15 lines of
its log are displayed by default. If you specify the -f option, then the
continuing logs for all started services are displayed by a separate process
which you can terminate without affecting the running services.

Options:
    -f, --follow               Display log files using a separate process.
ENDUp

$LDOC{down} = <<ENDDown;

Usage:  {NAME} down [OPTIONS] [SERVICE...]

Bring down the specified service or all running services, remove containers
and networks. You can use any options available for the 'docker-compose down'
command, except for --rmi and --volumes which are ignored for safety reasons.
We don't want the main database, which is stored on a volume, to be accidentally
deleted, and we provide a different facility for managing container images.

Options:
    --remove-orphans    Also remove containers for services not defined in the
                        Compose file
ENDDown

$LDOC{start} = <<ENDStart;

Usage:  {NAME} start [OPTIONS] [SERVICE...]

Start services that were previously stopped. If no services are specified,
then all stopped services are started. If you start a single process, the
last few lines of its service log file are displayed by default. If you
specify -f, the continuing log file(s) are displayed using a separate
process so that you can terminate the display without affecting the running
services.

Options:
    -f, --follow               Display log files using a separate process.

ENDStart

$EDOC{stop} = "docker-compose help stop";
$LDOC{stop} = <<ENDStop;

Usage:  {NAME} stop [OPTIONS] [SERVICE...]

Bring down the specified services, but do not remove the containers. If no
services are specified, stop all of them.

Options:
ENDStop

$EDOC{kill} = "docker-compose help kill";
$LDOC{kill} = <<ENDKill;

Usage:  {NAME} kill [OPTIONS] [SERVICE...]

Force-stop the specified services, but do not remove the containers. Like
stop, but sends a signal (default SIGKILL) to each container. If no
services are specified, kill all of them.

Options:
ENDKill

$EDOC{restart} = "docker-compose help restart";
$LDOC{restart} = <<ENDRestart;

Usage:  {NAME} restart [OPTIONS] [SERVICE...]

Stop and restart the specified service(s). If you specify --rm, the service
container will be destroyed and a new container created. Otherwise, the
container's processes will be stopped and the container will be restarted
from its entrypoint with all local files intact. If you restart a single
service, the last few lines of the service log file will be displayed by default.
If you specify -f, the continuing log files of all restarted services will be
displayed using a separate process that can be terminated without affecting
the running services.

Options:
  -f, --follow               Display log files using a separate process.
  --rm                       Remove and recreate the running container.
ENDRestart

$LDOC{pause} = <<ENDPause;

Usage:  {NAME} pause [OPTIONS] [SERVICE...]

Suspend the specified services. The containers are fully preserved but will
be inactive and use no resources until subsequently restored to active status
with the 'unpause' command. If no services are specified, pause all of them.

ENDPause

$LDOC{unpause} = <<ENDUnpause;

Usage:  {NAME} unpause [OPTIONS] [SERVICE...]

Restore the specified services to full activity. If no services are specified,
unpause all of them.

ENDUnpause

$LDOC{top} = <<ENDTop;

Usage:  {NAME} top [SERVICE...]

Display the running processes for the specified service(s). If no service
is specified, display the running processes for all of them.

ENDTop

sub ControlCmd {

    # The command to be executed will be at the beginning of @ARGV.
    
    my $cmd = shift @ARGV;
    
    # Go through the arguments and handle all of the options we know about.
    
    my (@options, @names);
    my @services;
    my $opt_follow;
    my $opt_lines;
    my $opt_remove;
    
    foreach my $arg (@ARGV)
    {
	# # Handle a numeric argument to the 'logs' subcommand.
	
	# if ( $cmd eq 'docker-logs' && $arg =~ /^-*([0-9]+)$/ )
	# {
	#     $opt_lines = $1;
	#     next;
	# }
	
	# The following options are disallowed for safety reasons. They are silently ignored
	# except for with the subcommand 'down', where they cause the command to be aborted
	# with an error message.
	
	if ( $arg =~ /^(--rmi|-v|--volumes)$/ )
	{
	    next unless $cmd eq 'down';
	    print "ERROR: option '$arg' is not allowed with '$COMMAND down' for safety reasons\n";
	    exit 2;
	}
	
	# Other options with values are passed through to docker-compose.
	
	elsif ( $arg =~ /^(--\w[\w-]+=.*)/ )
	{
	    push @options, $arg;
	}
	
	# Options we know about are interpreted.

	elsif ( $arg =~ /^(-f|--follow|--rm|-q|--quiet)$/ )
	{
	    $opt_follow = 1 if $arg eq '-f' || $arg eq '--follow';
	    $opt_remove = 1 if $arg eq '--rm';
	    # ignore -q, --quiet
	    next;
	}
	
	# Other options without values are passed through to docker-compose, or else produce an
	# error result if badly formed.
	
	elsif ( $arg =~ /^(-\w|--[\w-]+)$/ )
	{
	    next if $arg eq '--quiet' || $arg eq '-q';
	    next if $arg eq '--rm' || $arg eq '-f' || $arg eq '--follow';
	    push @options, $arg;
	}
	
	elsif ( $arg =~ /^-/ )
	{
	    print "ERROR: unrecognized option '$arg'\n";
	    exit 2;
	}
	
	# Arguments that look like service names are collected up for later validation.
	
	elsif ( $arg =~ /^[a-z]\w*$/ )
	{
	    if ( $arg eq 'api' )
	    {
		$arg = 'pbapi' if $COMMAND eq 'pbdb';
		$arg = 'msapi' if $COMMAND eq 'macrostrat';
	    }
	    push @names, $arg;
	}
	
	else
	{
	    print "ERROR: unrecognized service '$arg'\n";
	    exit 2;
	}
    }

    # Determine the list of selected services. An argument of 'all' is equivalent to an empty
    # list.
    
    if ( @names && $names[0] ne 'all' )
    {
	my @list = grep { $_ =~ /[a-z]/i } map { split /\s*,\s*/, $_ } @names;
	
	@services = GetComposeServices({ exit_on_error => 1 }, @list);
    }
    
    # The 'up' subcommand always gets the arguments -d and --no-build.
    
    if ( $cmd eq 'up' )
    {
	unshift @options, '-d', '--no-build';
    }
    
    # # The 'logs' subcommand gets arguments indicating the number of lines to display. This subcommand
    # # has been renamed to 'docker-logs'.
    
    # if ( $cmd eq 'docker-logs' )
    # {
    # 	$cmd = 'logs';
    # 	unshift @options, '--tail', $opt_lines || 10;
    # 	unshift @options, '--follow' if $opt_follow;
    # }
    
    # If the specified subcommand was 'down' and there was at least one service specified, then we
    # substitute the 'rm' command and add the '--stop' option.
    
    if ( $cmd eq 'down' && @services )
    {
	$cmd = 'rm';
	unshift @options, '--stop';
	$opt_remove = undef; # the option --rm is redundant in this case, so ignore it
    }
    
    # This next step is crucial. If the subcommand is either 'down', 'stop', 'restart', or 'rm'
    # and mariadb is one of the services affected, then we must shut down the mysqld process
    # gracefully to avoid table corruption. The usual docker mechanism of sending a TERM signal
    # to pid 1 in the container does not work, because mysqld_safe ignores that signal.

    if ( $cmd eq 'down' || $cmd eq 'stop' || $cmd eq 'restart' || $cmd eq 'rm' )
    {
	# If @services is empty, then the current command will affect all services. Otherwise,
	# check to see if mariadb is in the list of affected services.
	
	if ( ! @services || grep /^(mariadb|mysql)$/, @services )
	{
	    # First figure out the container name.
	    
	    my ($base_name) = $MAIN_PATH =~ qr{ ([^/]+) /? $ }xs;
	    my $service = $CONFIG{database_container} || 'mariadb';
	    my $container_name = join('_', $base_name, $service, 1);
	    
	    # Then try to use 'mysqladmin shutdown'. The executive login has the SHUTDOWN
	    # privilege, which means we can use it to properly shut down the database server.
	    
	    my $success;
	    
	    if ( $CONFIG{exec_username} && $CONFIG{exec_password} )
	    {
		$success = SystemCommand('docker', 'exec', $container_name,
					 'mysqladmin', '--user', $CONFIG{exec_username},
					 '--password', $CONFIG{exec_password}, 'shutdown');
	    }
	    
	    if ( $success )
	    {
		print "Shutting down $service server...\n";
	    }
	    
	    # If mysqladmin fails for any reason, as a backup we try sending SIGTERM to the 'mysqld'
	    # process.
	    
	    else
	    {
		my @processes = CaptureCommand('docker', 'exec', $container_name, 'ps', '-e');

		chomp @processes;
		
		foreach my $line ( @processes )
		{
		    if ( $line =~ qr{ ^ \s* (\d+) .* \b mysqld $ }xs )
		    {
			my $process_id = $1;
			
			my $kill_success = SystemCommand('docker', 'exec', $container_name,
							 'kill', '-TERM', $process_id);

			if ( $kill_success )
			{
			    print "Shutting down $service server...\n";
			}
		    }
		}
	    }
	}
    }
    
    # If the specified command was 'restart' and the --rm option was specified, stop and remove
    # the running container and then start the service again. The --rm option is not valid with
    # any other command except for 'down', 'stop', and 'kill'.
    
    if ( $opt_remove )
    {
	if ( $cmd eq 'restart' )
	{
	    SystemDockerCompose('rm', '--stop', @services);
	    $cmd = 'up';
	    @options = ('-d');
	}
	
	elsif ( $cmd eq 'stop' || $cmd eq 'kill' )
	{
	    SystemDockerCompose($cmd, @services);
	    $cmd = 'rm';
	}
	
	else
	{
	    print "ERROR: The option --rm not valid with the subcommand '$cmd'\n";
	    exit 2;
	}
    }
    
    # Execute the specified command.
    
    SystemDockerCompose($cmd, @options, @services);
    
    # If the command was 'logs' or 'top', then stop now.
    
    # return if $cmd eq 'docker-logs' || $cmd eq 'top';
    
    return if $cmd eq 'top';
    
    # If the container is starting or restarting, allow 2 seconds and then display the container
    # status and container log.
    
    if ( $cmd eq 'start' || $cmd eq 'up' || $cmd eq 'restart' )
    {
	sleep(2);
	DisplayStatus(@services);
	if ( $opt_follow )
	{
	    ExecDockerCompose('logs', '--tail', '30', '--follow', @services);
	}
	else
	{
	    ExecDockerCompose('logs', '--tail', '15', @services);
	}
    }
    
    # Otherwise, display the status unless we were told not to.
    
    else
    {
	return DisplayStatus(@services);
    }
}


# LogCmd ( )
# 
# This routine implements the subcommand 'log' (alias logs).

$LDOC{log} = <<ENDLog;

Usage:  {NAME} log [OPTIONS] [SERVICE] [FILE]
        {NAME} log ls [OPTIONS] [SERVICE] [FILE]
        {NAME} log docker [SERVICE]

Lists log files, or displays the most recent entries from the specified log file.

The first form of this command prints out the last 15 lines of the specified file, or some other
number of lines if specified. The -f option causes the command to keep running and output appended
lines as the file grows, just as with 'tail -f '. If only the SERVICE parameter is given, the most
recently modified log file associated with that service is selected. If the FILE parameter is
given in addition, the most recently modified log file whose name matches FILE is selected. If
FILE is 'docker', then the docker log for the specified service is selected.

The second form of this command lists all matching log files. By default they are listed in
alphabetical order, but you can use the -t option to list them by most recently modified. Each
file is listed with its size and how long ago it was last modified.

The third form of this command lists the docker logs corresponding to the specified service, or
all of them if no service is specified.

Options:
    -[n], [n]       Display the last n lines from the log. The default is 15.
    -f, --follow    Follow log output.
    -l, --list      List log files.
    -t              Print the list in order of most recently modified rather than alphabetically.
ENDLog

sub LogCmd {

    my ($cmd) = shift @ARGV;
    
    my $log_dir = $CONFIG{log_dir} || 'logs';
    
    # Go through the arguments and handle all of the options we know about.
    
    my ($opt_lines, $opt_follow, $opt_list, $opt_docker, $opt_order, @param);
    
    foreach my $arg (@ARGV)
    {
	# Handle a numeric argument.
	
	if ( $arg =~ /^-*([0-9]+)$/ )
	{
	    $opt_lines = $1;
	    next;
	}
	
	# Options and subcommands that we know about are interpreted.
	
	elsif ( $arg =~ /^(-+f|--follow|-+t|-+lt|-+l|--list|list|ls|docker)$/ )
	{
	    $opt_follow = 1 if $arg =~ /-f/;
	    $opt_order = 'mod' if $arg =~ /-t|-lt/;
	    $opt_list = 1 if $arg =~ /-l|ls|list/;
	    $opt_docker = 1 if $arg eq 'docker';
	    next;
	}
	
	# Other options produce an error.
	
	elsif ( $arg =~ /^-/ )
	{
	    print "ERROR: unrecognized option '$arg'\n";
	    exit 2;
	}

	# Arguments which are not options are added to the @param array.

	elsif ( defined $arg && $arg ne '' )
	{
	    push @param, $arg;
	}
    }

    # The default for number of lines is 10.
    
    $opt_lines ||= 10;
    
    # If one of the arguments was 'docker', then exec the command 'docker-compose logs' and pass all
    # other non-option arguments plus any options that are relevant.
    
    if ( $opt_docker )
    {
	unshift @param, '--follow' if $opt_follow;
	unshift @param, "--tail=$opt_lines";
	ExecDockerCompose('logs', @param);
    }
    
    # If we were given no arguments at all, list all the subdirectories of the logs directory that
    # contain log files. If the old names 'pbdb-classic' and 'pbdb-new' are found, substitute
    # 'classic' and 'pbapi' respectively.
    
    elsif ( @param == 0 && ! $opt_list )
    {
	print "The following services have log files:\n";
	
	my @list = ListLogs($log_dir, $opt_order, 'dirs');
	
	foreach my $name ( @list )
	{
	    $name = 'classic' if $name eq 'pbdb-classic';
	    $name = 'pbapi' if $name eq 'pbdb-new';
	    print "$name\n";
	}
	
	return;
    }

    # Otherwise, get a list of all the log files that match the first non-option non-subcommand
    # parameter. If there is no non-empty parameter, all log files will be listed.
    
    $opt_order = 'mod' unless $opt_list;
    
    my @list = ListLogs($log_dir, $opt_order, 'full', $param[0]);
    
    unless ( @list )
    {
	print "No logs were found for '$param[0]'\n";
	exit 2;
    }
    
    # If a second parameter was given, filter the list accordingly.
    
    if ( $param[1] )
    {
	my $filter = qr{ [/] .* $param[1] }xs;
	
	@list = grep { $_ =~ $filter } @list;
    }
    
    unless ( @list )
    {
	print "No logs matching '$param[1]' were found for '$param[0]'\n";
	exit 2;
    }
    
    # If we were asked to list the log files, do so. For each file, include the size and the
    # number of minutes, hours, or days since it was last modified.
    
    if ( $opt_list )
    {
	my (@name, @size, @elapsed);
	
	foreach my $filename ( @list )
	{
	    push @name, $filename;
	    
	    my $log_size = -s "$log_dir/$filename";
	    
	    if ( $log_size > 1048576 )
	    {
		push @size, int($log_size / 1048576) . 'M';
	    }

	    elsif ( $log_size > 1024 )
	    {
		push @size, int($log_size / 1024) . 'K';
	    }
	    
	    else
	    {
		push @size, $log_size . 'B';
	    }
	    
	    my $mod_elapsed = -M _;
	    
	    if ( $mod_elapsed >= 2 )
	    {
		push @elapsed, int($mod_elapsed) . ' days';
	    }

	    elsif ( $mod_elapsed >= 1 )
	    {
		push @elapsed, "1 day";
	    }

	    elsif ( int($mod_elapsed*24) >= 1 )
	    {
		push @elapsed, int($mod_elapsed*24) . ' hr';
	    }

	    elsif ( int($mod_elapsed*1440) >= 1 )
	    {
		push @elapsed, int($mod_elapsed*1440) . ' min';
	    }

	    else
	    {
		push @elapsed, int($mod_elapsed*86400) . ' sec';
	    }
	}
	
	PrintOutputList({ format => ['', 'R'] }, undef, \@name, \@size, \@elapsed);
    }
    
    # Otherwise, execute the 'tail' command on the first file in the (filtered) list.
    
    else
    {
	my @cmd = ('tail', '-n', $opt_lines);
	push @cmd, '-f' if $opt_follow;
	push @cmd, "$log_dir/$list[0]";
	
	ExecCommand(@cmd);
    }
}


sub ListLogs {
    
    my ($log_dir, $order, $mode, $selector) = @_;
    
    $selector = 'pbapi' if $selector eq 'api' && $COMMAND eq 'pbdb';
    $selector = 'msapi' if $selector eq 'api' && $COMMAND eq 'macrostrat';
    $selector = '' if $selector eq 'all' || $mode eq 'all';
    
    my $opt = $order ? '-lt' : '-l';
    
    my @lines = CaptureCommand("cd $log_dir; ls $opt */*");
    
    my (@result, @secondary, %found);
    
    foreach my $line (@lines)
    {
	if ( $line =~ qr{ \d\d:\d\d \s+ (\S+) [/] (.*) }xs )
	{
	    my $dirname = $1;
	    my $logname = $2;
	    chomp $logname;
	    
	    if ( $mode eq 'dirs' && ! $found{$dirname} )
	    {
		push @result, $dirname;
		$found{$dirname} = 1;
	    }
	    
	    elsif ( $mode eq 'full' && (! $selector || $dirname eq $selector) )
	    {
		push @result, "$dirname/$logname";
	    }
	}
    }

    if ( $mode eq 'full' && $selector && ! @result )
    {
	foreach my $line (@lines)
	{
	    if ( $line =~ qr{ \d\d:\d\d \s+ (\S+) [/] (.*) }xs )
	    {
		my $dirname = $1;
		my $logname = $2;
		chomp $logname;
		
		if ( $logname =~ /$selector/ )
		{
		    push @result, "$dirname/$logname";
		}
	    }
	}
    }
    
    return @result;
}


# ExecCmd ( )
#
# This routine implements the subcommands 'exec' and 'run'.

$EDOC{exec} = "docker-compose help exec";
$LDOC{exec} = <<ENDExec;

Usage:  {NAME} exec [OPTIONS] SERVICE COMMAND [ARGS...]

Execute a command in a the running container for the specified service.
All options are passed along to 'docker exec'.

Options:
ENDExec

$EDOC{run} = "docker-compose help run";
$LDOC{run} = <<ENDRun;

Usage:  {NAME} run [OPTIONS] SERVICE COMMAND [ARGS...]

Execute a one-off command in a new container, using the image built for the specified
service. All options are passed through to 'docker-compose run'.

Options:
ENDRun

sub ExecCmd {

    my $cmd = shift @ARGV;
    
    # Go through the argument list. The service or container may be specified either before
    # or after the option list, unlike in the underlying docker or docker-compose commands.
    
    my @options;
    my $label;
    
    if ( $ARGV[0] && $ARGV[0] !~ /^-/ )
    {
	$label = shift @ARGV;
    }
    
    while ( $ARGV[0] =~ /^-/ )
    {
	if ( $ARGV[0] =~ qr{ ^ (?: -e | --env | -u | --user | --workdir ) $ }xs )
	{
	    push @options, shift @ARGV;
	    push @options, shift @ARGV;
	}
	
	else
	{
	    push @options, shift @ARGV;
	}
    }
    
    unless ( $label )
    {
	$label = shift @ARGV;
    }
    
    # The subcommand 'exec' is implemented using the 'docker exec' command.
    
    if ( $cmd eq 'exec' )
    {
	unless ( $label && @ARGV )
	{
	    print "ERROR: You must specify a container or service followed by a command.\n";
	    exit 2;
	}
	
	# If a full container name was not given, we need to construct one.
	
	my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
	my $container;
	
	if ( $label eq 'api' )
	{
	    $label = 'pbapi' if $COMMAND eq 'pbdb';
	    $label = 'msapi' if $COMMAND eq 'macrostrat';
	}

	elsif ( $label eq 'mysql' )
	{
	    $label = $CONFIG{database_container} || 'mariadb';
	}
	
	# There are three possibilities: either a full container name starting with the base name
	# was given, or else a service name, or else the name of some other container.
	
	if ( $label =~ /^$base_name/ )
	{
	    $container = $label;
	}
	
	elsif ( $label =~ /_/ )
	{
	    $container = join('_', $base_name, $label);
	}
	
	else
	{
	    $container = join('_', $base_name, $label, 1);
	}
	
	# Quickly run through the options list, and take out -T if it was specified.
	
	my @clean_options;
	my $has_it;
	
	foreach my $opt ( @options )
	{
	    $has_it = 1 if $opt eq '-it';
	    push @clean_options, $opt unless $opt eq '-T';
	}
	
	# If there is only a single command to be run and it looks like a shell, then add -it to
	# the options unless that was already specified.

	if ( @ARGV == 1 && $ARGV[0] =~ /^[a-z]*sh$/ )
	{
	    unshift @clean_options, '-it' unless $has_it;
	}
	
	# Now check for shell metacharacters in the rest of the arguments. If so, the command will
	# need to be executed as "sh -c ...".
	
	my $argstring= join(' ', @ARGV);
	
	if ( $argstring =~ /[?*<>|;&]/ )
	{
	    ExecCommand('docker', 'exec', @clean_options, $container, 'sh', '-c', $argstring);
	}
	
	# Otherwise, the command can be executed as a list.
	
	else
	{
	    ExecCommand('docker', 'exec', @clean_options, $container, @ARGV);
	}
    }
    
    # Otherwise, we use docker-compose to create a new container based on the service name.

    else
    {
	unless ( $label && @ARGV )
	{
	    print "ERROR: You must specify a service followed by a command.\n";
	    exit 2;
	}
	
	# Make sure that the service is one that is actually defined.
	
	my ($service) = GetComposeServices($label);
	
	unless ( $service )
	{
	    print "ERROR: '$label' is not a $COMMAND service.\n";
	    exit 2;
	}
	
	# Quickly run through the options list, and take out -i, -t, or -it if any of these was
	# specified. Add --rm, because we don't want run containers hanging around after they
	# exit.
	
	my @clean_options = ('--rm');
	
	foreach my $opt ( @options )
	{
	    push @clean_options, $opt unless $opt eq '-i' || $opt eq '-t' || $opt eq '-it';
	}
	
	# Now check for shell metacharacters in the rest of the arguments. If so, they will need to be
	# executed as 'sh -c "..."'.
	
	my $argstring= join(' ', @ARGV);
	
	if ( $argstring =~ /[?*<>|;&]/ )
	{
	    ExecDockerCompose('run', @clean_options, $service, 'sh', '-c', $argstring);
	}
	
	# Otherwise, the command can be executed as a list.
	
	else
	{
	    ExecDockerCompose('run', @clean_options, $service, @ARGV);
	}	
    }
}


# MariadbCmd ( )
# 
# This routine implements the subcommand 'mariadb'.

$LDOC{mariadb} = <<ENDMysql;

Usage:  {NAME} mariadb [OPTIONS] [DATABASE] [COMMAND]

Start a mariadb (mysql) command-line client in the container in which MariaDB is
running. Any options and arguments that you specify other than those listed below
will be passed to this program. The subcommand 'mysql' is an alias for this command.

Unless you specify otherwise, the mariadb client will be run as the executive user.

If you specify a different command name that begins with the prefix 'mysql'
or 'mariadb' such as 'mysqladmin', that command will be executed instead.

Options:
  --user, -u          Run the client as the specified user. You may specify
                      the name of any installed component, in which case the
                      username used by that component's API will be used.
  --root, -R          Invoke the client process as the mariadb root user.
  --exec, -E          Invoke the client process as the executive user.

ENDMysql

my %USER_MAP = ( paleobiodb => 'pbdb',
		 pbdb => 'pbdb',
		 macrostrat => 'macro',
		 macro => 'macro',
		 rockd => 'rockd',
		 mibasin => 'mibas',
		 mibas => 'mibas' );

my %DB_MAP = ( pbdb => 'pbdb',
	       macro => 'macrostrat',
	       mibas => 'ummpfriends' );

sub MariadbCmd {

    my $cmd = shift @ARGV;
    
    ReadLocalConfig;
    
    my $username = $CONFIG{exec_username};
    my $password = $CONFIG{exec_password};
    my $database;
    my $command;
    my @initargs;
    my @args;
    
    while ( @ARGV )
    {
	if ( $ARGV[0] =~ /^--root$|^-R$/ )
	{
	    ($username, $password) = (undef, undef);
	    shift @ARGV;
	}
	
	elsif ( $ARGV[0] =~ /^--exec$|^-E$/ )
	{
	    shift @ARGV;
	}
	
	elsif ( $ARGV[0] =~ /^--user$|^-u$|^--user=(.*)/ )
	{
	    shift @ARGV;
	    $username = ($1 || shift @ARGV);
	    $password = undef;
	    
	    if ( my $selector = $USER_MAP{$username} )
	    {
		if ( $CONFIG{"${selector}_username"} )
		{
		    $username = $CONFIG{"${selector}_username"};
		    $password = $CONFIG{"${selector}_password"};
		    $database = $DB_MAP{$selector};
		}
	    }
	}
	
	elsif ( $ARGV[0] =~ /^--password=(.*)|^-p$/ )
	{
	    shift @ARGV;
	    $password = $1;
	}
	
	elsif ( $ARGV[0] =~ /^--[\w-]+=/ )
	{
	    push @args, shift @ARGV;
	}

	elsif ( $ARGV[0] =~ /^-e$/ )
	{
	    shift @ARGV;
	    $command = shift @ARGV;
	}
	
	else
	{
	    push @args, shift @ARGV;
	}
    }
    
    if ( $args[-1] =~ /[^\w-]/ )
    {
	$command = pop @args;
    }

    if ( $args[-1] =~ /^[\w-]+$/ )
    {
	$database = pop @args;
    }
    
    if ( $username )
    {
	push @initargs, "--user=$username";
	
	if ( $password )
	{
	    push @initargs, "--password=$password";
	}
	
	else
	{
	    push @initargs, "--password";
	}
    }
    
    push @initargs, '-A' if $cmd eq 'mysql' || $cmd eq 'mariadb';

    push @initargs, '-e', $command if $command;

    push @initargs, $database if $database;
    
    my $db_container = join('_', $MAIN_NAME, 'mariadb_1');
    
    if ( -t STDIN && ! $command )
    {
	ExecCommand('docker', 'exec', '-it', $db_container, $cmd, @initargs, @args);
    }
    
    else
    {
	ExecCommand('docker', 'exec', '-i', $db_container, $cmd, @initargs, @args);
    }
}


# PostgresqlCmd ( )
# 
# This routine implements the subcommand 'mariadb'.

$LDOC{psql} = <<ENDPsql;

Usage:  {NAME} psql [OPTIONS] [DATABASE] [COMMAND]

Start a postgresql command-line client (psql) in the container in which Postgresql is
running. Any options and arguments that you specify other than those listed below
will be passed to this program.

Unless you specify otherwise, the postgresql client will be run as the executive user.

Options:
  --user, -u          Run the client as the specified user. You may specify
                      the name of any installed component, in which case the
                      username used by that component's API will be used.
  --root, -R          Invoke the client process as the postgres (root) user.
  --exec, -E          Invoke the client process as the executive user.

ENDPsql


my %DB_MAP_PSQL = ( macro => 'burwell',
		    rockd => 'rockd' );

sub PostgresqlCmd {

    my $cmd = shift @ARGV;
    
    ReadLocalConfig;
    
    my $username = $CONFIG{exec_username};
    my $database;
    my $command;
    my @initargs;
    my @args;
    
    while ( @ARGV )
    {
	if ( $ARGV[0] =~ /^--root$|^-R$/ )
	{
	    $username = 'postgres';
	    shift @ARGV;
	}
	
	elsif ( $ARGV[0] =~ /^--exec$|^-E$/ )
	{
	    shift @ARGV;
	}
	
	elsif ( $ARGV[0] =~ /^--user$|^-u$|^--user=(.*)/ )
	{
	    shift @ARGV;
	    $username = $1 || shift @ARGV;
	    
	    if ( my $selector = $USER_MAP{$username} )
	    {
		if ( $username = $CONFIG{"${selector}_user"} )
		{
		    $database = $DB_MAP_PSQL{$selector};
		}
	    }
	}
	
	elsif ( $ARGV[0] =~ /^--password=(.*)|^-p$/ )
	{
	    shift @ARGV;
	}
	
	elsif ( $ARGV[0] =~ /^--[\w-]+=/ )
	{
	    push @args, shift @ARGV;
	}

	elsif ( $ARGV[0] =~ /^-c$/ )
	{
	    shift @ARGV;
	    $command = shift @ARGV;
	}
	
	else
	{
	    push @args, shift @ARGV;
	}
    }
    
    if ( $args[-1] =~ /[^\w-]/ )
    {
	$command = pop @args;
    }

    if ( $args[-1] =~ /^[\w-]+$/ )
    {
	$database = pop @args;
    }
    
    if ( $username )
    {
	push @initargs, "--user=$username";
    }
    
    push @initargs, '-c', $command if $command;

    if ( $database )
    {
	push @args, $database;
    }

    else
    {
	push @args, 'postgres';
    }
    
    my $db_container = join('_', $MAIN_NAME, 'postgresql_1');
    
    if ( -t STDIN && ! $command )
    {
	ExecCommand('docker', 'exec', '-it', $db_container, $cmd, @initargs, @args);
    }
    
    else
    {
	ExecCommand('docker', 'exec', '-i', $db_container, $cmd, @initargs, @args);
    }
}


# ShellCmd ( )
#
# This routine implements the subcommand 'shell'.

$LDOC{sh} = <<ENDShell;

Usage:  {NAME} sh [OPTIONS] SERVICE

Start an interactive shell in the running container for the specified service.
This will be bash if it exists in that image, or sh otherwise.

Options:
    --privileged      Give extended privileges to the process.
    -u, --user USER   Run the shell as this user.

ENDShell

sub ShellCmd {

    my ($opt_privileged, $opt_user, $opt_run);
    
    my $cmd = shift @ARGV;
    
    die "Invalid command '$cmd'\n" unless $cmd eq 'sh' || $cmd eq 'shell';
    
    GetOptions( "privileged" => \$opt_privileged,
		"user|u=s" => \$opt_user,
	        "run" => \$opt_run );

    # First determine which service we will be creating the shell in.
    
    my $service = shift @ARGV;
    
    die "You must specify the name of a service.\n" unless $service;

    if ( @ARGV )
    {
	my $rest = join(' ', @ARGV);
	warn "Ignored: $rest\n";
    }

    if ( $service eq 'api' )
    {
	$service = 'pbapi' if $COMMAND eq 'pbdb';
	$service = 'msapi' if $COMMAND eq 'macrostrat';
    }
    
    my @options;
    
    push @options, "--privileged" if $opt_privileged;
    push @options, "--user", $opt_user if $opt_user;

    # Check the status of the service. If it is up, we use "docker-compose exec" to spawn a shell
    # process in the running container. But if the --run option was specified, then create it in a
    # new container instead.
    
    my $status = GetServiceStatus($service);
    
    if ( $status =~ /up/i && ! $opt_run )
    {
	my $check = CaptureDockerCompose('exec', '-T', $service, 'which', 'bash');
	
	if ( $check =~ /bash/ )
	{
	    print "Running bash in the container 'paleobiodb_${service}_1':\n";
	    ExecDockerCompose('exec', @options, $service, 'bash');
	}
	
	else
	{
	    print "Running sh in the container 'paleobiodb_${service}_1':\n";
	    ExecDockerCompose('exec', @options, $service, 'sh');
	}
    }

    # If there is no running container, or if the --run option was given, we use "docker-compose
    # run" to spawn a shell process in a new container using the image generated for this service.

    else
    {
	my $check = CaptureDockerCompose('run', '-T', '--rm', $service, 'which', 'bash');

	if ( $check =~ /bash/ )
	{
	    print "Running bash in a new container with the image for service '$service':\n";
	    ExecDockerCompose('run', @options, '--rm', $service, 'bash');
	}

	else
	{
	    print "Running sh in a new container with the image for service '$service':\n";
	    ExecDockerCompose('run', @options, '--rm', $service, 'sh');
	}
    }
}


# DoCmd ( )
#
# This subroutine implements the command 'do'.

$LDOC{do} = <<ENDDo;

Usage:  {NAME} do [OPTIONS] TASK...

Execute one or more tasks from the list of tasks known to this command. The
tasks will be executed in sequence, with each being started after the previous
one has finished. If any task returns a non-zero result code, an error line
will be printed out. A result code of zero will be returned if all tasks
return zero, otherwise the last non-zero code will be returned.

This command is designed to be run either from a crontab or directly from
the command line. You can use the following options to control what output
is generated and where that output is directed.

Options:

  --log, -l       Causes each task to append all output to its own default log
                  file instead of sending it to standard output. This option or
                  the lack of it can be overridden for particular tasks by including
                  either an explicit 'log' or 'stdout' argument.

  --notify, -n    At the end of every task that returns a result code of zero,
                  print a line indicating that the task has succeeded. If you
                  include this option in a cron job, you will get an emailed
                  report every time the job runs regardless of whether the tasks
                  succeeded or failed. If you don't include --notify but do
                  include --log, then successful tasks will produce no ouptut
                  and you will get an email only if one or more tasks fail.

You can include modifiers between tasks or after the last task. The
accepted modifiers are:

  if-ok           If the preceding command returned a non-zero result code
                  to indicate that it did not complete successfully,
                  terminate the task sequence immediately and do not execute
                  the rest of the tasks. You can also express this modifier as &&.

A task can either be a simple task_name, or else task_name(args). In the latter
case, the task will be run with the specified arguments split up on whitespace.

Available tasks are:

ENDDo

my ($LOG_OPEN);

sub DoCmd {
    
    my ($cmd) = shift @ARGV;
    
    ReadLocalConfig;
    
    # Start by processing any arguments to this subcommand.
    
    my ($opt_log, $opt_notify);
    
    Getopt::Long::Configure("bundling");
    
    GetOptions( "log|l" => \$opt_log,
		"notify|n" => \$opt_notify );
    
    # Choose the appropriate task list based on which command is being executed right now.
    
    my $taskfunc;
    
    if ( $COMMAND eq 'macrostrat' )
    {
	require "PMCmd/MSTasks.pm";
	$taskfunc = \%PMCmd::MSTasks::TASK;
    }
    
    else
    {
	require "PMCmd/PBTasks.pm";
	$taskfunc = \%PMCmd::PBTasks::TASK;
    }
    
    # Then go through the rest of the arguments one by one. Group together any elements in
    # parentheses, to make a single task specification with arguments.
    
    my @task_queue;
    my ($arg, $value, $inopts, $inquote);
    my ($task, @options);
    my $failsafe = 200;
    
    while ( @ARGV || (defined $arg && $arg ne '') )
    {
	die "Parse error: infinite loop\n" unless --$failsafe;
	
	unless ( defined $arg && $arg =~ /\S/ )
	{
	    $arg = shift @ARGV;
	    next unless defined $arg && $arg =~ /\S/;
	}
	
	unless ( $task )
	{
	    @options = ();
	    $inopts = undef;
	    $inquote = undef;
	    
	    if ( $arg =~ qr{ ^ \s* ([a-z][\w-]+|&&) (?: $ | \s+ (.*) ) }xsi )
	    {
		push @task_queue, [undef, $1];
		$arg = $2;
		next;
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* ([a-z][\w-]+) [(] (.*) }xsi )
	    {
		$task = $1;
		$arg = $2;
		$inopts = 1;
	    }
	    
	    else
	    {
		my $next = substr(join(' ', $arg, @ARGV), 0, 20);
		die "Syntax error at '$next': task name expected\n";
	    }
	}
	
	next unless $arg =~ /\S/;
	
	if ( $inquote )
	{
	    if ( $inquote && $arg =~ qr{ ^ (\\.) (.*) }xs )
	    {
		$value .= $1;
		$arg = $2;
	    }
	    
	    if ( $inquote eq q{'} && $arg =~ qr{ ^ ([^'\\]*) ([']?) (.*) }xs )
	    {
		$value .= $1;
		$arg = $3;
		
		if ( $2 )
		{
		    push @options, $value;
		    $inquote = undef;
		}
	    }
	    
	    elsif ( $inquote eq q{"} && $arg =~ qr{ ^ ([^"]*) (["]?) (.*) }xs )
	    {
		$value .= $1;
		$arg = $3;

		if ( $2 )
		{
		    push @options, $value;
		    $inquote = undef;
		}
	    }
	    
	    else
	    {
		my $next = substr(join(' ', $arg, @ARGV), 0, 20);
		die "Syntax error at '$next': quote error $inquote\n";
	    }
	    
	    next;
	}
	
	elsif ( $inopts )
	{
	    if ( $arg =~ qr{ ^ \s* [)] (?: $ | \s+ (.*) ) }xs )
	    {
		push @task_queue, [undef, $task, @options];
		$task = undef;
		$inopts = undef;
		$arg = $1;
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* ([()]) (.*) }xs )
	    {
		my $next = substr(join(' ', "$1$2", @ARGV), 0, 20);
		die "Syntax error at '$next': unexpected $1\n";
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* -* ([\w-]+) (?: $ | ([)] .*) | \s+ (.*) ) }xs )
	    {
		push @options, $1;
		$arg = ($2 ne '' ? $2 : $3)
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* -* ([\w-]+) [=] (?! ['"] ) ([^()\s]*) (.*) }xs )
	    {
		push @options, "$1=$2";
		$arg = $3;
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* -* ([\w-]+) [=] ['] ([^'\\]*) ([']?) (.*) }xs )
	    {
		if ( $3 )
		{
		    push @options, "$1=$2";
		}
		
		else
		{
		    $value = "$1=$2";
		    $inquote = q{'};
		}
		
		$arg = $4;		
	    }
	    
	    elsif ( $arg =~ qr{ ^ \s* -* ([\w-]+) [=] ["] ([^"\\]*) (["]?) (.*) }xs )
	    {
		if ( $3 )
		{
		    push @options, "$1=$2";
		    $arg = $4;
		}
		
		else
		{
		    $value = "$1=$2";
		    $inquote = q{"};
		}

		$arg = $4;
	    }
	    
	    else
	    {
		my $next = substr(join(' ', $arg, @ARGV), 0, 20);
		die "Syntax error at '$next': option name expected";
	    }
	    
	    next;
	}

	else
	{
	    next;
	}
    }
    
    # If we have an unclosed parenthesis or quoted string, that is a syntax error.
    
    if ( $inquote )
    {
	$value =~ s/^.*?=/$inquote/;
	die "Syntax error: unterminated quote $value\n";
    }
    
    elsif ( $inopts )
    {
	my $next = substr("$task(" . join(' ', @options), 0, 20);
	die "Syntax error: unclosed parentheses at '$next'\n";
    }
    
    # Preserve standard output so we can switch back to it after directing output to a log file.
    
    open(SAVE_STDOUT, '>&STDOUT');
    select(STDOUT);
    $| = 1;
    
    # Now go through the task queue and execute the tasks one by one.
    
    my @result_list;
    
  TASK:
    while ( @task_queue )
    {
	my $task_record = shift @task_queue;
	my ($rc, $task, @options) = @$task_record;
	
	my $log_filename;
	
	# If the output of the previous task was directed to a log file, and that file hasn't yet
	# been closed for some reason, close it now and return standard output to its usual
	# destination. This is a failsafe and should never actually execute.
	
	if ( $LOG_OPEN )
	{
	    close STDOUT;
	    open(STDOUT, '>&SAVE_STDOUT');
	    $LOG_OPEN = 0;
	}
	
	# If the task is a modifier, execute it now. The 'if-ok' modifier terminates execution of
	# the task queue unless the previous task executed successfully.
	
	if ( $task eq 'if-ok' || $task eq '&&' )
	{
	    if ( $result_list[-1] && $result_list[-1] =~ /^\d+$/ )
	    {
		print "Execution terminated with some tasks remaining.\n" if @task_queue;
		exit $result_list[-1];
	    }
	    
	    else
	    {
		next TASK;
	    }
	}
	
	# Otherwise, construct the full task specification for use in reporting results.
	
	my $full;
	
	if ( @options )
	{
	    $full = "$task(";
	    my $sep = '';
	    
	    foreach my $opt ( @options )
	    {
		if ( ref $opt eq 'HASH' )
		{
		    while ( my ($key, $value) = each %$opt )
		    {
			$full .= "$sep$key=$value";
			$sep = ' ';
		    }
		}
		
		else
		{
		    $full .= "$sep$opt";
		    $sep = ' ';
		}
	    }
	    
	    $full .= ")";
	}
	
	else
	{
	    $full = $task;
	}
	
	# If the options list includes 'all' or 'config', read options from the corresponding
	# configuration setting. For each matching set of options, generate a separate task
	# record. Put these on the queue and then go back to start executing the first of them.
	
	my @opt_config = grep /^all$|^config$|^config=/, @options;
	
	if ( @opt_config )
	{
	    my @other_opts = grep !/^all$|^config$|^config=/, @options;
	    my @config_list;
	    
	    my $config_name = ( $COMMAND eq 'macrostrat' ? $PMCmd::MSTasks::TASK_CONFIG{$task}
				                         : $PMCmd::PBTasks::TASK_CONFIG{$task} );
	    
	    unless ( $config_name )
	    {
		print STDERR "ERROR: no configuration setting is defined for task '$task'.\n";
		push @result_list, $full, 10;
		next TASK;
	    }
	    
	    unless ( $CONFIG{$config_name} )
	    {
		print STDERR "ERROR: no value was found for configuration setting '$config_name'.\n";
		push @result_list, $full, 10;
		next TASK;
	    }
	    
	    foreach my $opt_config ( @opt_config )
	    {
		if ( $opt_config =~ /=(.*)/ )
		{
		    my $selector = $1;
		    
		    if ( my $opts = TaskConfigSelect($config_name, $selector) )
		    {
			push @config_list, $opts;
		    }
		    
		    else
		    {
			print STDERR "\nERROR for $task: no configuration matching '$selector' was found.\n\n";
			push @result_list, $full, 10;
			next TASK;
		    }
		}
		
		else
		{
		    unless ( @config_list = TaskConfigAll($config_name) )
		    {
			print STDERR "\nERROR for $task: the configuration did not have a usable value.\n\n";
			push @result_list, $full, 10;
			next TASK;
		    }
		}
	    }
	    
	    @options = (@config_list, @other_opts);
	}
	
	# If the options list includes 'log', or if the global option --log was given, determine
	# the log file name. If none was given, use the one found in the corresponding
	# 'task_logfile' configuration setting. If we can't find a filename from there, make one
	# by appending '.log' to the name of the task.
	
	my ($opt_task_log) = grep /^log($|=)/, @options;
	
	if ( $opt_task_log || $opt_log )
	{
	    my $log_file;
	    
	    # If the options list includes 'stdout', that overrides $opt_log for this task. The
	    # filename will be left empty, so standard output will not be redirected.
	    
	    if ( grep /^stdout$/, @options )
	    {
		# do not redirect standard output
	    }
	    
	    # Otherwise, if a log file name has been explicitly given, output will be directed to
	    # that file.
	    
	    elsif ( $opt_task_log && $opt_task_log =~ /=(.*)/ )
	    {
		$log_filename = $1;
	    }

	    # Otherwise, look up the corresponding entry in the configuration setting 'task_logfile'.
	    
	    elsif ( $CONFIG{task_logfile}{$task} )
	    {
		$log_filename = $CONFIG{task_logfile}{$task};
	    }

	    # If none is found, use the default filename $task.log.
	    
	    else
	    {
		$log_filename = "$task.log";
	    }

	    @options = grep !/^log($|=)/, @options;
	}
	
	# Now see if this function is one we know how to do.
	
	my $function = $taskfunc->{$task};
	my $result;
	
	# If there is a corresponding procedure to execute, do so now. If a logfile was specified,
	# open it first.
	
	if ( $function && $function =~ qr{ ^ ( PMCmd::\w+ ) }xs )
	{
	    # Start by requiring the module in which the task subroutine is located, in case we
	    # haven't loaded it yet.
	    
	    no strict 'refs';
	    
	    my $module = $1;
	    $module =~ s{::}{/}g;
	    require "$module.pm";
	    
	    # If standard output is to be directed to a log file, do so now.
	    
	    if ( $log_filename )
	    {
		if ( open(STDOUT, '>>', "$MAIN_PATH/logs/$log_filename") )
		{
		    $LOG_OPEN = 1;
		}
		
		else
		{
		    print STDERR "Could not open $MAIN_PATH/logs/$log_filename: $!\n";
		}
	    }
	    
	    select(STDOUT);
	    $| = 1;
	    
	    # Execute the subroutine in an eval block. If an exception is thrown, we will mark this task
	    # as having failed and move on to the next one.
	    
	    $DB::single = 1;
	    
	    eval {
		$result = &{$function}($task, @options);
	    };
	    
	    # If an exception was thrown, then the task has failed. Print out the error message to
	    # both STDOUT (the log) and STDERR (cron job mailto if this is being run from cron), add
	    # the task to the result list, and go on to the next task.
	    
	    if ( $@ )
	    {
		print STDOUT $@;
		print STDERR $@;
		push @result_list, $full, -1;
		next TASK;
	    }
	}
	
	# If the entry in $taskfunc does not have the proper form, inform the user and go on to
	# the next task.
	
	elsif ( $function )
	{
	    print STDOUT "ERROR: internal entry for '$task' has improper format.\n";
	    push @result_list, $full, -1;
	    next TASK;
	}
	
	# If the task is not one we recognize at all, see if there is a matching program we can
	# execute in the same directory as the current executable.
	
	else
	{
	    # Check the path of the current executable, typically /usr/local/bin or some such.
	    
	    my $found;
	    
	    if ( $0 =~ qr{ ^ ( / .* ) / \w+ $ }xs )
	    {
		my $dirpath = $1;
		my @checkpath = ("$dirpath/$COMMAND-$task", "$dirpath/$task");
		
	      PATH:
		foreach my $execfile ( @checkpath )
		{
		    next PATH unless -e $execfile;
		    
		    # If we find a matching command, make sure it is executable.
		    
		    unless ( -x $execfile )
		    {
			print STDOUT "ERROR: cannot execute $execfile: $!\n";
			push @result_list, $full, 2;
			next TASK;
		    }
		    
		    # Redirect standard output if directed.
		    
		    if ( $log_filename )
		    {
			if ( open(STDOUT, '>>', "$MAIN_PATH/logs/$log_filename") )
			{
			    $LOG_OPEN = 1;
			}
			
			else
			{
			    print STDOUT "Could not open $MAIN_PATH/logs/$log_filename: $!\n";
			}
		    }
		    
		    # Set some environment variables.
		    
		    $ENV{PALEOMACRO_ROOT} = $MAIN_PATH;
		    $ENV{PALEOMACRO_CONFIG} = "$MAIN_PATH/$PMCmd::Config::LOCAL_CONFIG";
		    $ENV{PALEOMACRO_COMPOSE} = "$MAIN_PATH/$PMCmd::Config::MASTER_COMPOSE";
		    $ENV{PALEOMACRO_LOCAL_COMPOSE} = "$MAIN_PATH/$PMCmd::Config::LOCAL_COMPOSE";
		    $ENV{PALEOMACRO_DEBUG} = 1 if $DEBUG;
		    
		    # Now call that program with the specified arguments.
		    
		    SystemCommand($execfile, @options);
		    $result = ResultCode();
		    $found = 1;
		    last PATH;
		}
	    }
	    
	    unless ( $found )
	    {
		print STDOUT "ERROR: don't know how to do '$task'.\n";
		push @result_list, $full, -1;
		next TASK;
	    }
	}
	
	# If standard output was redirected, put it back now.
	
	if ( $LOG_OPEN )
	{
	    close STDOUT;
	    open(STDOUT, '>&SAVE_STDOUT');
	    $LOG_OPEN = 0;
	}
	
	# Task subroutines should return 0 for success, so if $result is true then the task
	# failed. If an exception was thrown, the task also failed and in this case we use the
	# result code -1.
	
	if ( $result )
	{
	    print "Task $full failed with result code $result.\n";
	}
	
	# Otherwise, the task succeeded. If the global option --notify was given, print out a
	# notification of success. If --log is specified and --notify is not, there will be no
	# output unless a task fails or prints something to STDERR.
	
	elsif ( $opt_notify )
	{
	    print "Task $full succeeded.\n";
	}
	
	# Add the full task specification string and result code to @result_list.
	
	push @result_list, $full, ($result || 0);
	next TASK;
    }
    
    # If we get here, then the last task completed. We go through the result codes and return
    # either the last non-zero result or zero.

    my $rc = 0;
    
    while ( @result_list )
    {
	my $task = shift @result_list;
	my $result = shift @result_list;
	$rc = $result if $result;
    }
    
    exit $rc;
}


# TaskConfigSelect ( configname, selector )
# 
# Return the configuration information stored under $configname in the main configuration
# file config.yml. Select just the record indicated by $selector.

sub TaskConfigSelect {

    my ($config_name, $selector) = @_;
    
    return unless $selector;

    if ( ref $CONFIG{$config_name} eq 'HASH' )
    {
	return $CONFIG{$config_name}{$selector} if $CONFIG{$config_name}{$selector} &&
	    ref $CONFIG{$config_name}{$selector} eq 'HASH';
	
	return $CONFIG{$config_name} if $CONFIG{$config_name}{name} && ! ref $CONFIG{$config_name}{name} &&
	    $CONFIG{$config_name}{name} eq $selector;
    }

    elsif ( ref $CONFIG{$config_name} eq 'ARRAY' )
    {
	foreach my $entry ( @{$CONFIG{$config_name}} )
	{
	    return $entry if defined $entry->{name} && $entry->{name} eq $selector;
	}
    }
    
    else
    {
	print STDERR "ERROR: the value of configuration setting '$config_name' is not an arrayref or a hashref.\n";
    }
    
    return;
}


# TaskConfigAll ( configname )
# 
# Return a list of configuration records stored under $config_name in the main configuration file.

sub TaskConfigAll {

    my ($config_name) = @_;
    
    if ( ref $CONFIG{$config_name} eq 'HASH' )
    {
	my @records;
	
	foreach my $key ( sort keys %{$CONFIG{$config_name}} )
	{
	    push @records, $CONFIG{$config_name}{$key} if ref $CONFIG{$config_name}{$key} eq 'HASH' &&
		! $CONFIG{$config_name}{$key}{inactive};
	}
	
	return @records;
    }
    
    elsif ( ref $CONFIG{$config_name} eq 'ARRAY' )
    {
	return grep { ref $_ eq 'HASH' && ! $_->{inactive} } @{$CONFIG{$config_name}};
    }
    
    else
    {
	print STDERR "ERROR: the value of configuration setting '$config_name' is not an arrayref or a hashref.\n";
    }
    
    return;
}


# TaskErrorMessage ( message )
#
# Print the specified message to STDERR, and also print it to STDOUT if STDOUT is open to a log
# file. This will result (under most circumstances) in the message being printed to both streams
# when they are directed differently, but only once if they are going to the same place.

sub TaskErrorMessage {
    
    my ($message) = @_;
    
    print STDOUT $message;
    
    if ( $LOG_OPEN )
    {
	print STDERR $message;
    }
}


# PrintOutputList ( options, header, column... )
#
# Print the specified data. If $options->{noformat} is true, then ignore the header and print out
# lines of tab-separated fields. Otherwise, print out a formatted table.

sub PrintOutputList {
    
    my ($options, $header, @columns) = @_;
    
    my $linelimit = $#{$columns[0]};
    
    my $columnpad = $options->{pad} // 5;

    my $outfh = $options->{outfh} || *STDOUT;
    
    # If the 'noformat' option was given, just print out lines of tab-separated fields.
    
    if ( $options->{noformat} )
    {
	foreach my $i ( 0..$linelimit )
	{
	    print join "\t", map { $_->[$i] // '' } @columns;
	    print "\n";
	}

	return;
    }
    
    # Otherwise, print formatted output.
    
    my (@width, @entrywidth, @separator, $format);
    
    # Start by computing column widths.
    
    foreach my $c ( 0..$#columns )
    {
	$width[$c] = StringWidth($header->[$c]);
	$separator[$c] = '-' x $width[$c];
	last if $c eq $#columns;
	
	foreach my $i ( 0..$linelimit )
	{
	    my $w = StringWidth($columns[$c][$i]);
	    $width[$c] = $w if $w > $width[$c];
	}
    }
    
    # # Create a format string.
    
    # $format = '%s';
    
    # foreach my $c ( 0..$#columns )
    # {
    #     my $mod = $options->{format}[$c] && $options->{format}[$c] =~ /R/ ? '' : '-';
    #     $format .= "%$mod$width[$c]s  ";
    # }
    
    # $format =~ s/\s*$/\n/;
    
    # print "format: $format\n" if $DEBUG;
    
    # If we were given a header list, print out the header followed by a separator line.
    
    if ( ref $header eq 'ARRAY' && @$header )
    {
	# print sprintf($format, '', @$header);
	# print sprintf($format, '', @separator);
	
	PrintLine(@$header);
	PrintLine(@separator);
    }
    
    # Print out the data lines.
    
    foreach my $i ( 0..$linelimit )
    {
	# print sprintf($format, '', map { $_->[$i] // '' } @columns);
	PrintLine(map { $_->[$i] // '' } @columns);
    }
    
    sub PrintLine {

	my (@fields) = @_;
	
	foreach my $j ( 0..$#fields )
	{
	    my $data = $fields[$j];
	    my $fieldwidth = $width[$j];
	    my $datawidth = StringWidth($data);
	    my $pad = $datawidth < $fieldwidth ? $fieldwidth - $datawidth : 0;
	    $pad += $columnpad if $j < $#fields;

	    print $outfh $data . (" " x $pad);
	}

	print $outfh "\n";
    }
}


sub StringWidth {
    
    my ($string) = @_;

    return 0 unless defined $string && $string ne '';
    $string =~ s/\033\[[\d;]+m//g;
    return length($string);
}


# HelpString ( command )
#
# Return the help string for the specified command.

sub HelpString {

    my ($cmd, $second) = @_;
    
    if ( $cmd eq 'do' )
    {
	my $module = $COMMAND eq 'macrostrat' ? 'PMCmd/MSTasks.pm' : 'PMCmd/PBTasks.pm';
	require $module;
	
	my $doc;
	my $max_len = 0;
	
	if ( $second )
	{
	    my $ldoc = $COMMAND eq 'macrostrat' ? \%PMCmd::MSTasks::LDOC : \%PMCmd::PBTasks::LDOC;
	    
	    if ( $ldoc->{$second} )
	    {
		return $ldoc->{$second};
	    }
	    
	    else
	    {
		$doc = <<EndError;
Unknown task '$second'

The available tasks are:

EndError
	    }
	}
	
	my $cdoc = $COMMAND eq 'macrostrat' ? \%PMCmd::MSTasks::CDOC : \%PMCmd::PBTasks::CDOC;
	my $clist = $COMMAND eq 'macrostrat' ? \@PMCmd::MSTasks::CLIST : \@PMCmd::PBTasks::CLIST;
	
	$doc ||= $LDOC{$cmd};

	if ( $clist && @$clist )
	{
	    foreach my $task ( @$clist )
	    {
		$max_len = length($task) if length($task) > $max_len;
	    }
	    
	    my $pattern = "  %-${max_len}s      \%s\n";
	    
	    foreach my $task ( @$clist )
	    {
		$doc .= sprintf($pattern, $task, $cdoc->{$task});
	    }
	    
	    $doc .= "\nRun $COMMAND help do [task] to get help on any of these tasks.\n\n";
	}
	
	else
	{
	    $doc .= "No tasks have been defined yet for $COMMAND.\n\n";
	}
	
	return $doc;
    }
    
    elsif ( $LDOC{$cmd} )
    {
	return $LDOC{$cmd}, $EDOC{$cmd};
    }

    else
    {
	return "\nNo documentation is available for the subcommand '$cmd'\n\n";
    }
}


1;
