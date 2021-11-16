#
# Paleobiology Database control command
#
# This module implements routines for interacting with the system.
#
# Author: Michael McClennen
# Created: 2019-12-05



use strict;

package PMCmd::System;

use parent 'Exporter';

use PMCmd::Config qw($MAIN_PATH $COMMAND $DEBUG);

our (@EXPORT_OK) = qw(GetComposeServices GetServiceStatus GetRunningServices
		      GetContainerID GetComposeYAML
		      ExecDockerCompose SystemDockerCompose CaptureDockerCompose
		      SystemCommand CaptureCommand ExecCommand PrintDebug ResultCode);

our ($RC);

our ($COMPOSE_YAML_CACHE);


# GetComposeServices ( )
#
# Return a list of services from the docker-compose configuration file. In order to avoid running
# docker-compose often, we cache the list in a file called .services. If that file cannot be read,
# or if either docker-compose.yml or docker-compose.override.yml is newer, then it will be
# re-created from the current list of services in docker-compose.yml and
# docker-compose.override.yml.

sub GetComposeServices {

    my @services;
    
    # Check for the cache file. If it is there, use its contents.  Otherwise, generate the list of
    # services and try to write them to the file.  Ignore any errors that may occur, because on
    # subsequent invocations if no cache is available then we will simply keep trying to write it.
    
    my $cachefile = "$MAIN_PATH/.services";
    
    # unless ( @internal_list = ReadCachedServices($cachefile) )
    # {
    # 	require YAML::Tiny;
    # 	require Scalar::Util;
	
    #     # Get the list of services from docker-compose.
	
    #     @internal_list = CaptureDockerCompose('config', '--services');
	
    # 	# Then get the entire docker-compose configuration in YAML format. This will enable us to
    # 	# mark services that have been deliberately disabled.
	
    # 	my $config_yaml = CaptureDockerCompose('config') || '';
    # 	my $yaml_root = YAML::Tiny->read_string($config_yaml);
	
    # 	if ( $yaml_root && Scalar::Util::reftype($yaml_root) &&
    # 	     Scalar::Util::reftype($yaml_root) eq 'ARRAY' &&
    # 	     Scalar::Util::reftype($yaml_root->[0]) &&
    # 	     Scalar::Util::reftype($yaml_root->[0]) eq 'HASH' )
    # 	{
    # 	    $yaml_root = $yaml_root->[0];
    # 	}
	
    # 	if ( $yaml_root && Scalar::Util::reftype($yaml_root->{services}) eq 'HASH' )
    # 	{
    # 	    foreach my $s ( @internal_list )
    # 	    {
    # 		if ( $yaml_root->{services}{$s}{entrypoint} &&
    # 		     Scalar::Util::reftype($yaml_root->{services}{$s}{entrypoint}) eq 'ARRAY' &&
    # 		     grep /disabled/i, @{$yaml_root->{services}{$s}{entrypoint}} )
    # 		{
    # 		    $s = "$s*";
    # 		}
    # 	    }
    # 	}
	
    # 	# Then write the list to the cache file
	
    # 	if ( open(my $outfh, ">", $cachefile) )
    # 	{
    # 	    PrintDebug("Writing: list of services to .services") if $DEBUG;
    # 	    print $outfh map { "$_\n" } @internal_list;
    # 	    close $outfh;
    # 	}
    # }
    
    unless ( @services = ReadCachedServices($cachefile) )
    {
        @services = CaptureDockerCompose('config', '--services');
        
        if ( open(my $outfh, ">", $cachefile) )
        {
            PrintDebug("Writing: list of services to .services") if $DEBUG;
            print $outfh @services;
            close $outfh;
        }
	
	chomp @services;
    }
    
    # If the first argument is a hashref, it specifies arguments.
    
    my ($opt_exit, $opt_skip_disabled);
    
    if ( ref $_[0] eq 'HASH' )
    {
	$opt_exit = 1 if $_[0]->{exit_on_error};
	$opt_skip_disabled = 1 if $_[0]->{skip_disabled};
	shift @_;
    }
    
    # Either filter out disabled services or remove the marks.
    
    # my @services;
    
    # foreach my $s ( @internal_list )
    # {
    # 	if ( $s =~ /(.*)[*]$/ )
    # 	{
    # 	    push @services, $1 unless $opt_skip_disabled;
    # 	}
	
    # 	else
    # 	{
    # 	    push @services, $s;
    # 	}
    # }
    
    # Return the whole list unless there were any arguments given, or if 'all' was specified.
    
    return @services unless @_;
    return @services if $_[0] eq 'all';
    
    # Otherwise, use this list to validate the arguments.
    
    my %filter = map { $_ => 1 } @services;
    my @result;
    my $error;

    foreach my $arg ( @_ )
    {
	# The argument 'api' is substituted with either 'pbapi' or 'msapi' depending whether this
	# subroutine was called from the 'pbdb' or 'macrostrat' command.
	
	if ( $arg eq 'api' )
	{
	    $arg = 'pbapi' if $COMMAND eq 'pbdb';
	    $arg = 'msapi' if $COMMAND eq 'macrostrat';
	}
	
	# We allow 'mysql' as a synonym for 'mariadb'.
	
	elsif ( $arg eq 'mysql' )
	{
	    $arg = 'mariadb';
	}
	
	# Now filter out everything that does not match an actual service.
	
	if ( $filter{$arg} ) { push @result, $arg }
	else { print "ERROR: '$arg' is not a $COMMAND service.\n"; $error = 1 }
    }
    
    # If the 'exit_on_error' option was given, exit now. Otherwise, return the list.
    
    exit 2 if $error && $opt_exit;
    
    return @result;
}


# ReadCachedServices ( cachefile )
#
# Attempt to read a list of cached services from the specified file. If the file does not exist,
# or if either docker-compose.yml or docker-compose.override.yml is newer, then return nothing. If
# the file is unable to be read, return nothing. In all of those cases, the calling routine will
# read the list of services by executing docker-compose and if possible will create the file and
# write the list to it.

sub ReadCachedServices {

    my ($cachefile) = @_;
    
    return ( ) unless -M $cachefile;
    
    return ( ) if -M "$MAIN_PATH/docker-compose.yml" &&
	-M "$MAIN_PATH/docker-compose.yml" < -M $cachefile;
    
    return ( ) if -M "$MAIN_PATH/docker-compose.override.yml" &&
	-M "$MAIN_PATH/docker-compose.override.yml" < -M $cachefile;
    
    return ( ) unless open(my $infh, "<", $cachefile);
    
    PrintDebug("Reading: cached list of services from .services") if $DEBUG;
    
    chomp(my @output = <$infh>);
    close $infh;
    return @output;
}


# GetServiceStatus ( service )
#
# Return the status of the specified service.

sub GetServiceStatus {

    my ($service) = @_;
    
    return '' unless $service;
    
    my @lines = CaptureCommand('docker', 'ps', '--all', '--filter', "name=$service",
			       '--format', '{{.Label "com.docker.compose.service"}}::{{.Status}}::{{.Names}}');
    
    foreach my $line ( @lines )
    {
	my ($label, $status, $name) = split /::/, $line;
	
	if ( $label eq $service && $name !~ /_run_\d$/ )
	{
	    return $status;
	}
    }
    
    return '';
}


sub GetRunningServices {

    my @lines = CaptureCommand('docker', 'ps', '--filter', 'status=running',
			       '--filter', 'label=com.docker.compose.service',
			       '--format', '{{.Label "com.docker.compose.service"}}');
    
    return @lines;
}


# sub GetContainerStatus {
    
#     my ($name) = @_;
    
#     return '' unless $name;
    
#     my @lines = CaptureCommand('docker', 'ps', '--all', '--filter', "name=$name",
# 			       '--format', '{{.Names}}::{{.Status}}');

#     foreach my $line ( @lines )
#     {
# 	my ($names, $status) = split /::/, $line;
	
# 	if ( $names =~ /\b$name\b/ )
# 	{
# 	    return $status;
# 	}
#     }
    
#     return "No container";
# }

# GetContainerID ( service )
# 
# Map a docker-compose service name to a docker container id.

sub GetContainerID {

    my ($service) = @_;
    
    my $id = CaptureDockerCompose('ps', '-q', $service);
    $id = substr($id, 0, 15);
    
    unless ( $id =~ /^[a-z0-9]{15}$/i )
    {
	die "ERROR: No container found for '$service'\n";
    }
    
    return $id;
}


# # GetImageName ( service )
# # 
# # Map a docker-compose service name to a docker image name.

# sub GetImageName {
    
#     my ($service) = @_;
    
#     my @lines = CaptureCommand('docker', 'ps', '-a', '--filter', 'label=com.docker.compose.service',
# 			       '--format', '{{.Label "com.docker.compose.service"}}:::{{.Image}}');
    
#     foreach my $line ( @lines )
#     {
# 	my ($service_label, $image_label) = split /:::/, $line;
	
# 	if ( $service_label eq $service )
# 	{
# 	    return $image_label; 
# 	}
#     }
    
#     die "ERROR: no image found for service '$service'.\n";
# }


# ExecDockerCompose ( )
#
# Execute a docker-compose command with the specified arguments. This will terminate execution of
# the current script. Use the environment already set up by the current script. The output of the
# command will go to standard output, as if it had been executed directly from the command line.

sub ExecDockerCompose {
    
    my $paleobiodb_path = $ENV{PALEOBIODB_PATH} || $MAIN_PATH;
    my $paleobiodb_config = $ENV{PALEOBIODB_CONFIG};
    
    my @args = @_;
    unshift @args, '-f', $paleobiodb_config if $paleobiodb_config;
    
    PrintDebug("Executing: chdir $paleobiodb_path") if $DEBUG;
    
    chdir $paleobiodb_path;

    ExecCommand('docker-compose', @args);
}


# SystemDockerCompose ( )
#
# Execute a docker-compose command with the specified arguments, and then return to the current
# script. Use the environment already set up by the current script.

sub SystemDockerCompose {

    my $paleobiodb_path = $ENV{PALEOBIODB_PATH} || $MAIN_PATH;
    my $paleobiodb_config = $ENV{PALEOBIODB_CONFIG};

    my @args = @_;
    
    my $arg_count = scalar(@args);
    
    unshift @args, '-f', $paleobiodb_config if $paleobiodb_config;
    
    PrintDebug("Executing: chdir $paleobiodb_path") if $DEBUG;
    
    chdir $paleobiodb_path;

    if ( $arg_count > 1 )
    {
	return SystemCommand('docker-compose', @args);
    }
    
    else
    {
	return SystemCommand(join(' ', 'docker-compose', @args));
    }
}


# CaptureDockerCompose ( )
#
# Execute a docker-compose command with the specified arguments, and capture the output. Use the
# environment already set up by the current script.

sub CaptureDockerCompose {
    
    my $paleobiodb_path = $ENV{PALEOBIODB_PATH} || $MAIN_PATH;
    my $paleobiodb_config = $ENV{PALEOBIODB_CONFIG};

    my @args = @_;
    
    my $arg_count = scalar(@args);
    
    unshift @args, '-f', $paleobiodb_config if $paleobiodb_config;
    
    PrintDebug("#Executing: chdir $paleobiodb_path") if $DEBUG;
    
    chdir $paleobiodb_path;

    if ( $arg_count > 1 )
    {
	return CaptureCommand('docker-compose', @args);
    }

    else
    {
	return CaptureCommand(join(' ', 'docker-compose', @args));
    }
}


# GetComposeYAML ( )
#
# Return the contents of docker-compose.yml merged with docker-compose.override.yml as a Perl data
# structure.

sub GetComposeYAML {

    return $COMPOSE_YAML_CACHE if $COMPOSE_YAML_CACHE;
    
    my $config = CaptureCommand("cd $MAIN_PATH; docker-compose config");
    
    die "ERROR: Could not read docker-compose.yml or docker-compose.override.yml\n" unless $config =~ /\w/;
    
    require YAML::Tiny;
    require Scalar::Util;
    
    my $yaml_root = YAML::Tiny->read_string($config);
    
    die "ERROR: Could not parse docker-compose.yml\n" unless $yaml_root;
    
    if ( $yaml_root && Scalar::Util::reftype($yaml_root) && Scalar::Util::reftype($yaml_root) eq 'ARRAY' &&
	 Scalar::Util::reftype($yaml_root->[0]) && Scalar::Util::reftype($yaml_root->[0]) eq 'HASH' )
    {
	$yaml_root = $yaml_root->[0];
    }
    
    $COMPOSE_YAML_CACHE = $yaml_root;
    
    return $yaml_root;
}


# ExecCommand ( command, [args...] )
#
# Execute a command with the specified arguments. This will terminate execution of the current
# script. The output of the command will go to standard output, as if it had been executed
# directly from the command line. The primary purpose of this wrapper function is to print out the
# command before execution if debugging is turned on.

sub ExecCommand {

    PrintDebug(join(' ', "Executing: ", @_)) if $DEBUG;
    
    exec(@_);
}


# SystemCommand ( command, [args...] )
#
# Execute a command with the specified arguments, and then return to the current script. The
# output of the command will go to standard output, as if it had been executed directly from the
# command line. The primary purpose of this wrapper function is to print out the command before
# execution if debugging is turned on.

sub SystemCommand {
    
    $RC = undef;
    
    PrintDebug(join(' ', "Executing:", @_)) if $DEBUG;
    
    system(@_);
    
    if ( $? < 0 )
    {
	$RC = $?;
    }

    elsif ( $? > 0 )
    {
	$RC = ($? >> 8 || $?);
    }

    else
    {
	$RC = 0;
    }
    
    return !$RC;
}


sub CaptureCommand {
    
    my ($cmd, @args) = @_;
    
    $RC = undef;
    
    PrintDebug(join(' ', "Executing:", $cmd, @args)) if $DEBUG;
    
    open(my $infh, "-|", $cmd, @args) || die "ERROR: could not execute '$cmd': $!\n";
    
    my @output = <$infh>;
    close $infh;
    
    if ( $? < 0 )
    {
	$RC = $?;
    }
    
    elsif ( $? > 0 )
    {
	$RC = ($? >> 8 || $?);
    }
    
    else
    {
	$RC = 0;
    }
    
    if ( wantarray )
    {
	return @output;
    }
    
    else
    {
	return join('', @output);
    }
}



sub ResultCode {

    return $RC;
}


sub PrintDebug {
    
    my ($string, $prefix) = @_;
    
    if ( $prefix )
    {
	$string = "$prefix: $string";
    }
    
    # elsif ( $string !~ / ^ \w+ : /xs )
    # {
    # 	$string = "Executing: $string";
    # }
    
    print STDERR "# $string\n" if $DEBUG;
}

1;

