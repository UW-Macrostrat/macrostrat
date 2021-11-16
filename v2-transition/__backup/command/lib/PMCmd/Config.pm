#
# Paleomacro project installation and update command
#
# This module implements the configuration settings for this command.
# 
# Author: Michael McClennen
# Created: 2019-12-04


use strict;

package PMCmd::Config;

use parent 'Exporter';

use Carp qw(croak);

our @EXPORT_OK = qw(%CONFIG %DEFAULT %COMPONENT %BACKUP_NAME 
		    @INSTALLED_COMPONENTS @DB_COMPONENTS @WS_COMPONENTS @COMPONENT_CONF
		    $COMMAND $MAIN_PATH $MAIN_NAME $INSIDE_PATH $DEBUG $VERSION
		    $MASTER_COMPOSE $LOCAL_COMPOSE $LOCAL_CONFIG $WEBSITE_CONFIG
		    SetConfig ReadConfigFile ReadLocalConfig ReadConfigRaw WriteConfigRaw
		    AskQuestion AskChoice AskPassword MainName);

# The following variable holds default values for configuration settings. These values are copied
# into the %CONFIG hash before the main configuration file is read in. Consequently, the value of
# any setting in this hash can be overridden by an identically named variable in the main
# configuration file.

our %DEFAULT = ( main_component_data => 'project/component-data.yml',
		 main_setup_template => 'project/setup-template.yml',
		 main_compose_template => 'project/docker-compose-template.yml',
		 main_config_base => 'project/config-base.yml',
		 master_setup => 'setup.yml',
		 local_setup => 'setup.override.yml',
		 local_component_data => 'component-data.override.yml',
		 component_data_file => 'component/component-data.yml',
		 component_setup_template => 'component/setup-template.yml',
		 component_compose_template => 'component/docker-compose-template.yml',
		 component_nginx_template => 'component/nginx-dockerfile-template',
		 component_site_template => 'component/site-template.conf',
		 nginx_dockerfile_template => 'frontend/nginx/Dockerfile-template',
		 nginx_dockerfile => 'frontend/nginx/Dockerfile',
		 site_template => 'frontend/nginx/site-template.conf',
		 site_config => 'frontend/nginx/site.conf',
		 file_permissions => 'f0644',
		 project_choice => '',
		 include_paleobiodb => '',
		 include_macrostrat => '',
		 include_earthlife => '',
		 include_rockd => '',
		 include_mibasin => '',
		 site_paleobiodb => '',
		 site_macrostrat => '',
		 site_earthlife => '',
		 site_rockd => '',
		 site_mibasin => '',
		 volumes_dir => 'volumes',
		 pbdb_domain => '',
		 macro_domain => '',
		 website_paleobiodb => '',
		 website_macrostrat => '',
		 website_earthlife => '',
		 website_rockd => '',
		 website_mibasin => '',
		 website_local => '',
		 website_other_domain => '',
		 localsite_paleobiodb => '',
		 localsite_macrostrat => '',
		 localsite_earthlife => '',
		 localsite_rockd => '',
		 localsite_mibasin => '',
		 smtp_host => 'smtp.wiscmail.wisc.edu',
		 smtp_port => '25',
		 default_registry => 'registry.doit.wisc.edu/mmcclenn/paleobiodb-server',
		 letsencrypt_path => '',
		 unzip_cmd => 'gunzip -c',
		 backup_dir => '/backups/daily',
		 backup_filename => {
		     pbdb => 'pbdb-backup-SELECT',
		     wing => 'pbdb-wing-backup-SELECT',
		     core => 'pbdb-core-SELECT',
		     macrostrat => 'macrostrat-backup-SELECT' },
		 backup_database => {
		     pbdb => 'pbdb',
		     wing => 'pbdb_wing',
		     core => 'pbdb authorities collections ecotaph intervals interval_lookup measurements occurrences opinions permissions person pubs refs reidentifications secondary_refs specimens taxa_tree_cache',
		     macrostrat => 'macrostrat' },
		 backup_label => {
		     pbdb => 'the Paleobiology Database',
		     wing => 'the PBDB wing tables',
		     core => 'the PBDB core tables' },
		 pbdb_default_load => '',
		 pbdb_master_login => '',
		 pbdb_master_host => 'paleobiodb.org',
		 pbdb_proxy_host => '',
		 pbdb_master_backup_dir => '/backups/daily',
		 pbdb_master_image_dir => '/var/paleobiodb/images',
		 pbdb_master_archive_dir => '/var/paleobiodb/archives',
		 pbdb_master_datalog_dir => '/var/paleobiodb/datalogs',
		 pbdb_public_host => 'paleobiodb.org',
		 pbdb_public_backup_dir => '/backups/daily',
		 pbdb_public_image_dir => '/var/paleobiodb/images',
		 pbdb_public_archive_dir => '/var/paleobiodb/archives',
		 pbdb_public_datalog_dir => '/var/paleobiodb/datalogs',
		 macro_default_load => '',
		 macro_master_login => '',
		 macro_master_host => 'dev.macrostrat.org',
		 macro_proxy_host => '',
		 macro_master_backup_dir => '/backup3',
		 macro_public_host => 'macrostrat.org',
		 macro_public_backup_dir => '',
		 pbdb_username => 'pbdbuser',
		 pbdb_password => 'pbdbpwd',
		 macro_username => 'macrouser',
		 macro_password => 'macropwd',
		 rockd_username => 'rockduser',
		 rockd_password => 'rockdpwd',
		 mibas_username => 'mibasuser',
		 mibas_password => 'mibaspwd',
		 exec_username => 'execuser',
		 exec_password => 'execpwd',
		 log_dir => 'logs',
		 task_logfile => {
		     'build-tables' => 'build_log',
		     'paleo-coords' => 'paleocoord_log',
		     'rotate-logs' => 'rotation_log',
		     'backup' => 'backup_log',
		     'remote-sites' => 'backup_log',
		     'test' => 'test_log' },
		 service_rotation => {
		     'default' => { },
		     'pbapi' => { period => 'weekly', dir => 'pbapi', day => '2' },
		     'classic' => { period => 'weekly', dir => 'classic', day => '3' },
		     'nginx' => { period => 'weekly', dir => 'nginx', day => '4' } },
		 log_rotatation => {
		     'pbapi_log' => { service => 'pbapi',
				      indicator => 1,
				      keep => 1 },
		     'pbapi_error_log' => { service => 'pbapi',
					    keep => 1 },
		     'request_log' => { service => 'pbapi',
					keep => 1 },
		     'web_log' => { service => 'classic',
				    keep => 1 },
		     'classic_error_log' => { service => 'classic',
					      keep => 1 },
		     'rest_log' => { service => 'classic',
				     keep => 1 },
		     'taxa_cached_log' => { service => 'classic',
					    period => 'monthly',
					    keep => 1 },
		     'access.log' => { service => 'nginx',
				       keep => 4,
				       # process => 'pbdbstats >> /backups/stats/paleobiodb-org-YYYY-MM.txt',
				       # append => '/backups/accesslogs/paleobiodb-org-YYYY-MM.log',
				     },
		     'error.log' => { service => 'nginx',
				      keep => 4 },
		     'rotation_log' => { period => 'monthly',
					 empty_ok => 1,
					 keep => 1 },
		     'backup_log' => { period => 'monthly',
				       empty_ok => 1,
				       keep => 1 },
		     'build_log' => { period => 'monthly',
				      empty_ok => 1,
				      keep => 1 },
		     'paleocoord_log' => { period => 'monthly',
					   empty_ok => 1,
					   keep => 1 },
		     'test_log' => { period => 'monthly',
				     empty_ok => 1,
				     remove => 1 },
				   },
		 backup_log_file => 'backup_log',
		 build_log_file => 'build_log',
		 paleocoord_log_file => 'paleocoord_log',
		 database_service => 'mariadb',
		 postgres_service => 'postgres',
		 webserver_service => 'nginx' );

our (%STORE_ALWAYS) = ( file_permissions => 1,
			project_choice => 1,
			include_ => 1,
			backup_dir => 1,
			pbdb_master_ => 1,
			pbdb_public_ => 1,
			macro_master_ => 1,
			macro_public_ => 1,
			pbdb_username => 1,
			pbdb_password => 1,
			macro_username => 1,
			macro_password => 1,
			exec_username => 1,
			exec_password => 1 );

our %CONFIG;

our %COMPONENT;

our @INSTALLED_COMPONENTS;
our @DB_COMPONENTS;
our @WS_COMPONENTS;
our @COMPONENT_CONF;

# our @PROJECT_COMPONENTS = qw(paleobiodb earthlife macrostrat rockd mibasin);

# our %PROJECT_COMPONENT;

our $DEBUG;

our $VERSION = '1.5';

# The following variables hold the path of the directory in which the files for this installation
# are located, and the final component of that name.

our ($MAIN_PATH, $MAIN_NAME);

if ( $MAIN_PATH )
{
    $MAIN_PATH =~ qr{ ([^/]+) [/]? $ }xs || die "ERROR: could not determine last component of main path\n";
    $MAIN_NAME = $1;
}

# The following variable holds the path of the main directory into which project files are placed
# in container images.

our $INSIDE_PATH = '/var/paleomacro';

# The following variable reflects the command currently being executed. The possibilities are
# 'install', 'pbdb', and 'macrostrat'.

our $COMMAND = '';

# The following variables list the hardcoded path names used by this script. These are here so
# that if they need to be changed this one place in the code is all that needs to be updated.

our $MASTER_COMPOSE = "docker-compose.yml";
our $LOCAL_COMPOSE = "docker-compose.override.yml";

our $LOCAL_CONFIG = "config.yml";
our $WEBSITE_CONFIG = "website.yml";

# The following variable caches information read from config files.

our %CONFIG_CACHE;
our %CONFIG_SET;



# SetConfig ( )
# 
# Select an alternate local configuration file.

sub SetConfig {

    my ($filename) = @_;
    
    die "ERROR: could not read $filename: $!\n" unless -r $filename;
    $LOCAL_CONFIG = $filename;
}


# ReadLocalConfig ( )
#
# Read YAML data from the file $LOCAL_CONFIG and stuff it into %CONFIG so that other
# subroutines can use it.

sub ReadLocalConfig {
    
    my ($options) = @_;
    
    # If the local configuration file has already been read, return unless the no_cache option was
    # given.
    
    return 1 if %CONFIG && ! $options->{no_cache};
    
    # Read data from the local configuration file $LOCAL_CONFIG. This is 'config.yml' by default,
    # but can be overridden with the -f option.
    
    my $config_data = ReadConfigFile("$MAIN_PATH/$LOCAL_CONFIG", $options) ||
	die "ERROR: could not read $LOCAL_CONFIG. Aborting.\n";
    
    # Initialize the %CONFIG hash from the %DEFAULT hash. These values will stand unless
    # overridden by entries in $config_data.
    
    %CONFIG = %DEFAULT;
    
    # Now go through the keys from $config_data. Anything specified there overrides the default
    # values.
    
    foreach my $key ( keys %$config_data )
    {
	# Any default setting that is itself a hash can only be overridden by a hash, and
	# the sub-keys are overridden individually instead of the entire default hash being
	# overridden. If the entry in config.yml is not a hash, it is silently ignored.
	
	if ( ref $CONFIG{$key} eq 'HASH' )
	{
	    if ( $config_data->{$key} && ref $config_data->{$key} eq 'HASH' )
	    {
		foreach my $subkey ( keys %{$config_data->{$key}} )
		{
		    # We check down two levels for hash values in %CONFIG. This is enough for the
		    # current set of configuration settings, which have at most three levels
		    # (log_rotation).  If four-level settings are ever added, we will need to add
		    # a new layer to check.
		    
		    if ( ref $CONFIG{$key}{$subkey} eq 'HASH' )
		    {
			if ( $config_data->{$key}{$subkey} && ref $config_data->{$key}{$subkey} eq 'HASH' )
			{
			    foreach my $sskey ( keys %{$config_data->{$key}{$subkey}} )
			    {
				$CONFIG{$key}{$subkey}{$sskey} = $config_data->{$key}{$subkey}{$sskey};
				$CONFIG_SET{$key}{$subkey}{$sskey} = 1;
			    }
			}
		    }
		    
		    else
		    {
			$CONFIG{$key}{$subkey} = $config_data->{$key}{$subkey};
			$CONFIG_SET{$key}{$subkey} = 1;
		    }
		}
	    }
	}
	
	# A key defined in config.yml can override anything that does not have a default
	# definition, even if it is a hash or a list.
	
	elsif ( ! defined $CONFIG{$key} && ref $config_data->{$key} )
	{
	    $CONFIG{$key} = $config_data->{$key};
	    $CONFIG_SET{$key} = 1;
	}
	
	# If the default setting is not a reference, it can only be overridden by a scalar
	# value. In this case, just copy it over. A hashref or arrayref in config.yml is
	# silently ignored.
	
	elsif ( ! ref $config_data->{$key} )
	{
	    $CONFIG{$key} = $config_data->{$key};
	    $CONFIG_SET{$key} = 1;
	    
	    # A key of the pattern "include_x" indicates that component 'x' is part of this project
	    # installation if the value starts with 'y', and not otherwise.
	    
	    # if ( $key =~ /^include_(\w+)/ )
	    # {
	    # 	# my $component = $1;
	    # 	# $COMPONENT{$component} = { } if $CONFIG{$key} =~ /^y/i;
	    # }
	}
    }
    
    # Patch a few values that are needed elsewhere.

    if ( $CONFIG{main_config_base} && $PMCmd::Install::CONF_FILE{main} )
    {
	$PMCmd::Install::CONF_FILE{main}{basename} = $CONFIG{main_config_base};
    }

    return 1;
}


# ReadConfigFile ( filename )
# 
# Read YAML data from the specified file and return it. Return the first document in the
# contents, unless the top level is not a hash in which case an error is thrown.
#
# If this configuration file has already been read and its contents entered into %CONFIG_CACHE,
# return those contents.

sub ReadConfigFile {

    my ($filename, $options) = @_;
    
    $options ||= { };
    
    my $yaml_root;
    
    require YAML::Tiny;
    require Scalar::Util;
    
    if ( $CONFIG_CACHE{$filename} && ! $options->{no_cache} )
    {
	return $CONFIG_CACHE{$filename};
    }

    elsif ( -e $filename )
    {
	print "# Reading config file: $filename\n" if $DEBUG;
	
	eval {
	    $yaml_root = YAML::Tiny->read($filename);
	};

	if ( $@ )
	{
	    print STDERR "\nERROR: while reading $filename:\n    $@\n";
	    return;
	}
	
	if ( $yaml_root && ref($yaml_root) && Scalar::Util::reftype($yaml_root) eq 'ARRAY' )
	{
	    $yaml_root = $yaml_root->[0];
	}
	
	if ( $yaml_root && (ref $yaml_root eq 'HASH' || ref $yaml_root eq 'ARRAY' ) )
	{
	    $CONFIG_CACHE{$filename} = $yaml_root;
	    return $yaml_root;
	}

	elsif ( $options->{empty_ok} )
	{
	    $CONFIG_CACHE{$filename} = { };
	    return { };
	}
	
	else
	{
	    print STDERR "\nERROR: while reading $filename: contents must be a hash or array\n";
	    return;
	}
    }
    
    elsif ( $options->{absent_ok} )
    {
	print "# Skipping absent config file: $filename\n" if $DEBUG;
	
	return { };
    }
    
    else
    {
	print STDERR "\nERROR: $filename: not found\n";
	return;
    }
}


sub ReadConfigRaw {

    my ($filename) = @_;

    my ($infile, @content);
    
    unless ( open($infile, "<", $filename) )
    {
	print STDERR "WARNING: Could not open $filename: $!\n";
	return;
    }
    
    while ( my $line = <$infile> )
    {
	push @content, $line;
    }

    close $infile;
    
    return @content;
}


sub WriteConfigRaw {

    my ($filename, $content_ref) = @_;

    my $infile;

    open($infile, ">", $filename) || die "ERROR: could not write $filename: $!\n";
    
    print $infile @$content_ref;
    
    close $infile || die "ERROR: closing $filename on write: $!\n";
}


# MainName ( )
#
# Return the last component of $MAIN_PATH.

sub MainName {
    
    return $MAIN_NAME;
}


# AskQuestion ( prompt, options )
#
# Ask a question, wait for user input, and return the answer. 

sub AskQuestion {
    
    my ($prompt, $options) = @_;
    
    $options ||= { };
    
    croak "second argument must be an options hash" unless ref $options eq 'HASH';
    
    my $default = $options->{default};
    
    $prompt .= " " unless $prompt =~ / $/;
    
    if ( defined $default && $default ne '' )
    {
	$prompt .= "[$default] ";
    }
    
    print "\n$prompt";
    
    while (1)
    {
	my $answer = <STDIN>;
	chomp $answer;
	
	unless ( defined $answer && $answer ne '' )
	{
	    $answer = $default // '';
	}
	
	if ( $options->{yesno} || $options->{yesnoquit} )
	{
	    return 'yes' if $answer =~ /^y/i;
	    return 'no' if $answer =~ /^n/i;
	    return 'quit' if $answer =~ /^q/i && $options->{yesnoquit};
	    
	    my $list = $options->{yesnoquit} ? 'yes, no, or quit' : 'yes or no';
	    print "You must answer either $list to this question.\n\n$prompt";
	}
	
	elsif ( $options->{posint} )
	{
	    return $answer if $answer =~ /^\d+$/ && $answer > 0;
	    print "You must enter a positive integer value.\n\n$prompt";
	}
	
	elsif ( $options->{optional} || defined $answer && $answer ne '' )
	{
	    return $answer;
	}
	
	else
	{
	    print "You must answer this question.\n\n$prompt";
	    next;
	}
    }
}


# AskChoice ( prompt, options, [ choice, description ]... )
# 
# Ask the user to choose from a list of alternatives. Each one consists of a
# choice string and a corresponding description. The user is prompted in
# a loop until their input matches one of the choices. The default behavior
# is to return the description corresponding to the selected choice.
#
# Any alternative whose choice is '-' cannot be selected, nor will it be numbered.
# Such a choice can be used as a separator, with a description such as '-----------'.
# 
# The argument $options must be a hash, with keys as follows:
# 
#   default		Specify a default, which is selected if the user simply hits
#                       return. The value of this option can be any of the choices or
#                       any of the descriptions.
#   number_choices      If true, the choices are replaced by numbers. The user response is
#                       matched against these numbers instead of against the specified
#                       choices. If the value of this option is 'list', then the remaining
#                       arguments are all considered to be descriptions and are numbered
#                       in sequence. Otherwise, the choice strings are still recorded but not
#                       displayed.
#   return_choice       If the value of this option is true, then the selected choice
#                       is returned. If number_choices was given with a value other than
#                       'list', the choice corresponding to the selected number is returned.

sub AskChoice {

    my $prompt = shift @_;
    my $options = shift @_;
    
    croak "second argument must be an options hash" unless ref $options eq 'HASH';
    
    my $opt_number = $options->{number_choices} || '';
    my $opt_retchoice = $options->{return_choice};
    my $opt_default = $options->{default};
    
    my (@choices, %choice, $default_choice, $index);
    
    print "\n$prompt\n" if $prompt;
    
    while ( @_ )
    {
	my ($choice, $value, $desc);
	
	# The choice '-' is interpreted as a separator.
	
	if ( $_[0] eq '-' )
	{
	    $choice = shift @_;
	    $desc = $opt_number eq 'list' ? '---------' : shift @_;
	    print "     $desc\n";
	    next;
	}
	
	# If we are asked to number the alternatives, do so. If the value of this option is
	# 'list', then each argument counts as an alternative. Otherwise, each pair of arguments
	# counts as usual.
	
	elsif ( $opt_number )
	{
	    $choice = ++$index;
	    $value = $opt_number eq 'list' ? $choice : shift @_;
	    $desc = shift @_;
	}
	
	# Otherwise, we read a pair of arguments and interpret them as a choice and a description.
	
	else
	{
	    $choice = shift @_;
	    $value = $choice;
	    $desc = shift @_;
	}
	
	print "  $choice) $desc\n";
	push @choices, $choice;
	
	if ( $opt_retchoice )
	{
	    $choice{$choice} = $value;
	}

	else
	{
	    $choice{$choice} = $desc;
	}
	
	# If the value of the default option matches either the value or the description,
	# record this choice as the default.
	
	if ( defined $opt_default && ( $opt_default eq $value || $opt_default eq $desc ) )
	{
	    $default_choice = $choice;
	}
    }
    
    my $a = $choices[0];
    my $b = $choices[-1];
    
    my $guidestring = "$a-$b";
    
    if ( defined $default_choice && $default_choice ne '' )
    {
	$guidestring .= " [$default_choice]";
    }
    
    print "\nYou must choose an option from $guidestring: ";
    
    while (1)
    {
	my $answer = <STDIN>;
	chomp $answer;
	
	unless ( defined $answer && $answer ne '' )
	{
	    return $choice{$default_choice} if defined $default_choice;
	}
	
	if ( defined $answer && $answer ne '' && defined $choice{$answer} )
	{
	    return $choice{$answer};
	}
	
	else
	{
	    print "\nInvalid choice.\nYou must choose an option from $guidestring: ";
	    next;
	}
    }
}


# AskPassord ( prompt )
#
# Ask for a password. Turn off terminal echo until the user has finished responding.

sub AskPassword {

    my ($prompt) = @_;
    
    $prompt ||=  "Password:";
    
    eval {
	system "stty -echo";
    };
    
    my $passwd;
    
    eval {
	print "$prompt ";
	chomp($passwd = <STDIN>);
	print "\n";
    };
    
    eval {
	system "stty echo";
    };
    
    return $passwd;
}


1;
