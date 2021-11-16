#
# Paleobiology Database installation and update command
# 
# This module implements the guts of the paleobiodb installation command.
# 
# Author: Michael McClennen
# Created: 2019-12-13


use strict;

package PMCmd::Install;

use parent 'Exporter';

use PMCmd::Config qw(%CONFIG %DEFAULT %COMPONENT @INSTALLED_COMPONENTS @DB_COMPONENTS
		     $DEBUG $MAIN_PATH $COMMAND @COMPONENT_CONF
		     $MAIN_NAME $INSIDE_PATH $LOCAL_CONFIG $WEBSITE_CONFIG
		     ReadLocalConfig ReadConfigFile ReadConfigRaw WriteConfigRaw
		     AskQuestion AskChoice AskPassword);
use PMCmd::Command qw(DisplayStatus PrintOutputList);
use PMCmd::Build qw(BuildImage FindBuiltImage RebuildCopyMap BuildNginxDockerfile PushPullImages
		    ReadComponentData ListComponentTemplates ReadTemplate CheckTemplateTarget
		    GenerateFileFromTemplate GenerateYAMLFromTemplate BuildNginxDockerfile);
use PMCmd::DBVersion qw(ExecutiveCommand ExecutiveQuery);
use PMCmd::System qw(GetComposeServices GetServiceStatus GetRunningServices GetComposeYAML
		     GetContainerID PrintDebug ResultCode ExecCommand PrintDebug
		     SystemDockerCompose CaptureDockerCompose SystemCommand CaptureCommand);

use Scalar::Util qw(reftype);
use File::Copy;
use File::Path qw(make_path);
use Getopt::Long;
use Carp qw(carp croak);

our (@EXPORT_OK) = qw(IsInstallStep DoInstallStep StepLabel AllSteps);

our (%LDOC, %SDOC, %ADOC);


# The following variables list the installation steps and the corresponding routines.

our %INSTALL_STEP = ( project => \&ProjectStep,
		      codebase => \&CodebaseStep,
		      command => \&CommandStep,
		      config => \&ConfigStep,
		      build => \&BuildStep,
		      database => \&DatabaseStep,
		      mariadb => \&DatabaseStep,
		      postgresql => \&DatabaseStep,
		      content => \&ContentStep,
		      tasks => \&Taskstep,
		      website => \&WebsiteStep,
		      finish => \&FinishStep);

our %STEP_LABEL = ( project => "Step 1: [project] choose which project components to install",
		    codebase => "Step 2: [codebase] install the necessary components",
		    command => "Step 2a: [command] install the status and maintenance command",
		    config => "Step 3: [config] install or update configuration files",
		    build => "Step 4: [build] download base images and build container images",
		    database => "Step 5: [database] initialize databases",
		    mariadb => "Step 5a: [mariadb] initialize MariaDB",
		    postgresql => "Step 5b: [postgresql] initialize PostgreSQL",
		    content => "Step 6: [content] load database contents",
		    tasks => "Step 7: [tasks] configure database maintenance tasks",
		    website => "Step 8: [website] configure the website",
		    finish => "Step 9: [finish] bring up all services");

our @INSTALL_STEP = qw(start project codebase config build database content tasks website finish);

our %UPDATE_STEP = ( codebase => \&UpdateCodebaseCmd,
		     command => \&CommandStep,
		     setup => \&UpdateCodebaseCmd,
		     database => \&UpdateDatabaseCmd,
		     mariadb => \&UpdateDatabaseCmd,
		     postgresql => \&UpdateDatabaseCmd);

our %UPDATE_ALIAS = ( code => 'codebase',
		      repo => 'codebase',
		      repos => 'codebase',
		      mysql => 'mariadb',
		      contents => 'content',
		      images => 'image' );

our @UPDATE_STEP = qw(project codebase image command config database password root api content tasks website);

# our %CHECK_STEP = ( repos => \&RepoStep, repositories => \&RepoStep );

# our @CHECK_STEP = qw(repos);

our $MASTER_COMPOSE = "docker-compose.yml";
our $LOCAL_COMPOSE = "docker-compose.override.yml";
our $COMPOSE_OVERRIDE_BASE = "project/docker-compose.override.yml";
our $LOCAL_SETUP = "setup.override.yml";
our $SETUP_OVERRIDE_BASE = "project/setup.override.yml";
our $COMPONENT_OVERRIDE_BASE = "project/component-data.override.yml";

our %CHMOD_MAP = ( f0644 => 'og=rX',
		   f0640 => 'g=rX,o=',
		   f0600 => 'og=',
		   f0664 => 'g=rwX,o=rX',
		   f0660 => 'g=rwX,o=' );

# The following variables list the configuration files and provide information about how they
# should be initialized and updated.

our @MAIN_CONF = (
	      { component => 'main',
		filename => "config.yml",
		basename => "project/config-base.yml" },
		  
	      { component => 'nginx',
		service => 'nginx',
		filename => "frontend/nginx/nginx.conf",
		basename => "frontend/nginx/nginx-base.conf",
		subst => { nginx_workers => 'worker_processes;' } },
		  
	      { component => 'paleobiodb',
		service => 'pbapi',
		filename => "frontend/pbapi/config.yml",
		basename => "frontend/pbapi/config/config.base.yml",
		subst => { pbdb_username => 'username:',
			   pbdb_password => 'password:',
			   pbapi_workers => 'workers:', } },
		  
	      { component => 'paleobiodb',
		service => 'classic',
		filename => "frontend/classic/pbdb.conf",
		basename => "frontend/classic/pbdb.conf.base",
		subst => { pbdb_username => 'DB_USER=',
			   pbdb_password => 'DB_PASSWD=' } },
		  
	      { component => 'paleobiodb',
		service => 'classic',
		filename => "frontend/classic/config.yml",
		basename => "frontend/classic/config.yml.base",
		subst => { classic_workers => 'web_workers:' } },
		  
	      { component => 'paleobiodb',
		service => 'classic',
		filename => "frontend/classic/etc/log4perl.conf",
		basename => "frontend/classic/etc/log4perl.conf.base" },
		  
	      { component => 'paleobiodb',
		service => 'classic',
		filename => "frontend/classic/etc/wing.conf",
		basename => "frontend/classic/etc/wing.conf.base",
		subst => { pbdb_username => 'db:[',
			   pbdb_password => undef,
			   smtp_host => 'smtp:[',
			   smtp_port => undef,
			   pbdb_domain => 'sitename:',
			   site_paleobiodb => 'pbdb_site:' } },
		  
	      { component => 'earthlife',
		service => 'earthlife',
		filename => "frontend/earthlife/elc-api.uwsgi.ini",
		basename => "frontend/earthlife/elc-api.uwsgi.ini.base",
		subst => { earthlife_workers => 'processes=' } },
		  
		  # msapi => { component => 'macrostrat',
		  # 	      service => 'msapi',
		  # 	      filename => "frontend/msapi/v2/credentials.js",
		  # 	      basename => "frontend/msapi/v2/credentials.base.js",
		  # 	      subst => [
		  # 		    { setting => 'macro_username', pattern => 'user:', all => 1 },
		  # 		    { setting => 'macro_password', pattern => 'password:', all => 1 },
		  # 		    { setting => 'macro_mapzen_key', pattern => 'exports.mapzen_key=' },
		  # 		    { setting => 'macro_refresh_key', pattern => 'exports.cacheRefreshKey=' },
		  # 		       ] },
		  
		  # msapi1 => { component => 'macrostrat',
		  # 	       service => 'msapi',
		  # 	       filename => "frontend/msapi/v1/credentials.js",
		  # 	       basename => "frontend/msapi/v1/credentials.base.js",
		  # 	       subst => [ { setting => 'macro_username', pattern => 'user:', all => 1 },
		  # 		          { setting => 'macro_password', pattern => 'password:', all => 1 } ] },
		  # tileserver => { component => 'macrostrat',
		  # 		   service => 'msapi',
		  # 		   filename => "frontend/tileserver/credentials.js",
		  # 		   basename => "frontend/tileserver/credentials.base.js",
		  # 		   subst => { macro_username => 'pg_user:',
		  # 			      macro_password => 'pg_password:',
		  # 			      macro_tileserver_secret => 'secret:' } },
		  
		  # rockd => { component => 'rockd',
		  # 	      service => 'rockd',
		  # 	      filename => "frontend/rockd/api/v2/credentials.js",
		  # 	      basename => "frontend/rockd/api/v2/credentials.base.js",
		  # 	      subst => { macro_username => 'user:',
		  # 			 macro_password => 'password:',
		  # 			 rockd_mainpath => 'exports.mainPath=',
		  # 		         rockd_tokensecret => 'exports.tokenSecret=',
		  # 			 rockd_mail_key => 'apiKey:' } },
		  
		  # rockd1 => { component => 'rockd',
		  # 	       service => 'rockd',
		  # 	       filename => "frontend/rockd/api/v1/credentials.js",
		  # 	       basename => "frontend/rockd/api/v1/credentials.base.js",
		  # 	       subst => { macro_username => 'user:',
		  # 			  macro_password => 'password:',
		  # 			  rockd_mainpath => 'exports.mainPath=',
		  # 			  rockd_tokensecret => 'exports.tokenSecret=',
		  # 			  rockd_mail_key => 'apiKey:' } },
		  
		  # mibasin => { component => 'mibasin',
		  # 		service => 'mibasin',
		  # 		filename => "frontend/mibasin/routes/config.js",
		  # 		basename => "frontend/mibasin/routes/config.base.js",
		  # 		subst => { macro_username => 'user:',
		  # 			   macro_password => 'password:' } },
		 );

our %CONF_REBUILD = ( pbdb_username => [ 'pbapi', 'classic' ],
		      pbdb_password => [ 'pbapi', 'classic' ],
		      pbdb_domain => [ 'classic' ],
		      site_paleobiodb => [ 'classic' ],
		      macro_username => [ 'msapi', 'rockd', 'tileserver' ],
		      macro_password => [ 'msapi', 'rockd', 'tileserver' ] );

our %GIT_PERM = ( f0664 => 'all',
		  f0660 => 'group' );

our $MAIN_GROUP;

# The following variables list the domain names of the official sites for the available project
# components.

# our %PROJECT_LABEL = ( paleobiodb => "Paleobiology Database",
# 		       macrostrat => "Macrostrat",
# 		       earthlife => "Earthlife Consortium",
# 		       rockd => "Rockd",
# 		       mibasin => "Michigan Basin Fossils" );

our %repo_checked;
our $setup_file_changed;
our %rebuild_container;
our @SAVE_ARGV;

# IsInstallStep ( step_name )
#
# Return true if $step_name is a valid install step.

sub IsInstallStep {

    return $INSTALL_STEP{$_[0]};
}


# AllSteps ( )
#
# Return a list of all install steps.

sub AllSteps {
    return @INSTALL_STEP[1..$#INSTALL_STEP];
}


# StepLabel ( step )
# 
# Return the label string for the specified installation step.

sub StepLabel {
    return $STEP_LABEL{$_[0]};
}


# DoInstallStep ( step )
# 
# Execute the specified installation step.

sub DoInstallStep {

    my ($step) = @_;

    # Set the umask for this process according to the file permissions chosen during the
    # configuration process. We have to flip bits to go from a filemode to a umask. If no filemode
    # was set, default to 0664 -> 0002.

    my $raw_perm = $CONFIG{file_permissions} || 'f0664';
    my $umask = substr($raw_perm, 2, 3);
    $umask =~ tr/640/026/;
    
    umask "0$umask";
    
    PrintDebug("umask 0$umask") if $DEBUG;
    
    my $options = { install => $step };
    
    my $routine = $INSTALL_STEP{$step};
    
    if ( $routine )
    {
	return &$routine( $options );
    }
    
    else
    {
	die "ERROR: unknown installation step '$step'\n";
    }
}


# ShowCmd ( )
#
# List configuration files, settings, or other aspects of this installation.

$LDOC{show} = <<EndList;

Usage:  {NAME} show [OPTIONS] ARGUMENTS

Show information about one or more aspects of this installation. The available
options are:

  --no-format       Print out one line per list entry, with the fields separated by
                    tabs. Do not print any header, frame, or ANSI color codes.

  --no-color        Suppress ANSI color codes.

The things you can show are as follows:

  path              The name of the directory in which this installation is located.
  project           The project components that are active in this installation.
  repos             The git repositories that make up this installation.
  config settings   The settings from the main configuration file and their values.
  config all        All configuration settings including defaults.
  config files      The configuration files that are used by the various services.
  config            Without a second argument, lists the configuration settings.
  images            The docker images that have been downloaded and/or built.
  services          The services that make up the current installation.
  tasks             The automatic tasks that are being run for this installation.
  website           The currently active website configuration.

EndList

sub ShowCmd {

    my $cmd = shift @ARGV;
    
    # Read the configuration file and the component data.
    
    ReadLocalConfig;
    ReadComponentData;
    
    # Look for options before the update step name. We include common options here.
    
    my ($opt_noformat, $opt_nocolor, $opt_remote);
    
    Getopt::Long::Configure("permute");
    
    GetOptions( 'no-format' => \$opt_noformat,
	        'no-color' => \$opt_nocolor,
	        'origin' => \$opt_remote );
    
    $opt_nocolor = 1 if $opt_noformat;	# --no-format implies --no-color
    
    my $options = { };
    $options->{noformat} = 1 if $opt_noformat;
    $options->{nocolor} = 1 if $opt_nocolor;
    $options->{remote} = 1 if $opt_remote;
    
    my $subcmd = shift @ARGV;

    if ( $subcmd eq 'path' )
    {
	print "$MAIN_PATH\n";
    }
    
    elsif ( $subcmd eq 'project' || $subcmd eq 'components' )
    {
	return &ShowComponentsCmd($options);
    }
    
    elsif ( $subcmd eq 'repos' || $subcmd eq 'repositories' )
    {
	return &ShowReposCmd($options);
    }
    
    elsif ( $subcmd eq 'config' || $subcmd eq 'configuration' )
    {
	return &ShowConfigCmd($options);
    }
    
    elsif ( $subcmd eq 'images' )
    {
	return &ShowImagesCmd($options);
    }
    
    elsif ( $subcmd eq 'services' )
    {
	return &PMCmd::Command::ListServicesCmd($options);
    }
    
    elsif ( $subcmd eq 'tasks' )
    {
	return &ShowTasksCmd($options);
    }
    
    elsif ( $subcmd eq 'website' )
    {
	return &ShowWebsiteCmd($options);
    }
    
    else
    {
	print "Unknown subcommand '$subcmd'.\n";
    }
}

# UpdateCmd ( )
# 
# Execute one of the update steps as a subcommand. 

$LDOC{update} = <<EndUpdate;

Usage:  {NAME} update [OPTIONS] SUBCOMMAND [ARGUMENTS]

Update one or more parts of the installation. This command has subcommands that correspond
to the various installation steps, plus some additional subcommands.

If you want to update the current installation to reflect changes to the git repos and/or preload
images, you can run the subcommand 'update codebase'. This will pull all of the changes,
regenerate any setup and configuration files that have changed as a result, and rebuild containers
as necessary.

If you want to update the current installation to reflect changes to the Paleobiology Database
content or Macrostrat content, you can run the subcommand 'update content'.

If you want to change the way this installation is configured, you can run 'update project',
'update config', 'update tasks', and/or 'update website'.

If you want to change the way the database server(s) are configured, you can run the
command 'update database'. In this case, you can either choose which aspect of the database
to update with an additional command-line argument or else you will be asked which aspect
to update.

Subcommands are:
  
  command        Pull the base repository, reinstall the '{NAME}' command if changed
  project        Change the set of installed project components
  codebase       Pull all git repositories, rebuild anything whose source has changed
  setup          Rebuild the main setup files
  images         Check the container registry and pull any updated preload images
  config         Change settings for this installation
  database       Set database passwords or reinitialize the database(s).
  postgresql     Set database passwords or reinitialize the postgresql database.
  mariadb        Set database passwords or reinitialize the mariadb database.
  content        Update the database content
  tasks          Start, stop or reconfigure database maintenance tasks
  website        Change the website configuration for this installation.

Run '{NAME} help update SUBCOMMAND' to find out more about each of these. 

EndUpdate

$SDOC{update}{usage} = <<EndUsage;

Usage:  {NAME} update {SUBCOMMAND} {ARGS}
EndUsage

$SDOC{update}{project} = <<EndProject;

Change the set of installed project components. You will be asked which of the components
from the following list you want in this installation. If you add or remove components,
the files setup.yml, docker-compose.yml and config.yml will be rebuilt according to your
new selection and all repositories will be pulled.

Available components are:

  paleobiodb             Paleobiology Database
  macrostrat             Macrostrat
  earthlife              Earthlife Consortium website and API
  rockd                  Rockd API
  mibasin                Michigan Basin Fossils

EndProject

$ADOC{update}{codebase} = "[OPTIONS] [ARGUMENT]";

$SDOC{update}{codebase} = <<EndCodebase;

This command incorporates any changes to the project codebase into the current installation. If
run without any arguments, it starts by pulling the base repository and the base repositories for
all installed project components. If any the main setup files are out of date, you will be asked if
you want to rebuild them.  It then runs through all of the entries in setup.yml, and checks that
they are properly reflected in the directory tree. Any symlinks or directories that are not in
place will be created. Any git repositories will be checked, and if they are not up to date and
have no uncommitted changes they will be pulled.

Depending on what has changed, the {NAME} command may be reinstalled, preload images may be
pulled, and container images may be rebuilt. You will be asked before these step are done.

IMPORTANT: This is a potentially problematic subcommand, because it touches almost everything
in the installation. If any errors occur during execution of this command, you should do whatever
is necessary to fix them and execute the command again. It will do its best to pick up where it
left off and continue until everything is checked and rebuilt. In the interim, the installation
may not be completely functional.

You may also give it any of the following arguments:

  <component>         Checks and pulls only resources that are associated with the specified
                    project component, e.g. paleobiodb or macrostrat.

  <service>         Checks and pulls only resources that are associated with the specified
                    service, e.g. msapi or classic.

  tree              Checks and pulls all repositories except for the base repository.

  base              Checks and pulls only the base repository. If any of the main setup
                    files is out of date, you will be asked whether to rebuild it.

  setup             If any of the main setup files are out of date, you will be asked whether
                    to rebuild them.

  all               Pulls and rebuilds everything that has changed without asking.

Options include:

  --all             Pull and rebuild everything that has changed without asking.

  --force           Rebuild all generated files even if they are newer than the source
                    templates. Reinstall the '{NAME}' command even if none of the
                    source files have changed.

  --merge           Pull all repositories, even the ones with uncommitted changes. In those
                    cases, a git merge operation is done. If it fails, the repository head
                    will be reset back to where it was. WARNING: this is potentially
                    dangerous. It is better to use 'git stash' to set aside and save the
                    changes, then go back and run this command again.
  
  --registry=url    Use the specified registry URL for fetching preload images, instead
                    of the one listed in the config file.

  --origin=url      The the specified URL as the base for cloning git repositories rather
                    than the one specified in component-data.yml.

  --verbose, -v     Print out additional information about what is being done.

WARNING: if any of the repositories (including the base repository) have uncommitted
changes or are on a branch other than 'master', they will not be pulled. You can check this
by running '{NAME} show repos'. If there uncommitted changes in any repository, you can use
'git stash' to set them aside before running this command, then re-apply them if appropriate.

ANOTHER WARNING: in some cases, the changes you are incorporating may include additional
configuration settings for which you have not yet specified values. If you believe this
to be the case, you may want to follow up by running '{NAME} update config'.

EndCodebase

$ADOC{update}{setup} = "[OPTIONS] [ARGUMENT]";

$SDOC{update}{setup} = <<EndSetup;

Without any arguments, this command will check the files setup.yml, docker-compose.yml and
frontend/nginx/Dockerfile. Each file will be rebuilt if its corresponding source template is
newer.

If you specify the name of a project component on the command line, the repositories
and images associated with that component will be checked and pulled. If anything has changed,
the associated containers will be rebuilt. If you specify the name of a service, only the
repositories associated with that service will be checked and rebuilt. You can specify 'base'
to check just the base repository.

If it is necessary to rebuild the docker-compose file, you will be asked if you want all services
to be stopped before proceeding. After the command has run, you will be able to bring them up
again manually by executing '{NAME} up'.

If you specigy 

Rebuild the files setup.yml, docker-compose.yml, and frontend/nginx/Dockerfile from their
templates based on the current selection of project components, if any these files are newer
than the source template. You will be asked whether to rebuild each one.

Options include:

  --tree     Don't regenerate the files, just run through setup.yml and setup-override.yml
             and make sure that the directory tree matches the entries in those files.

  --force    Rebuild each file even if it is newer than the source template.

EndSetup

$ADOC{update}{command} = "[OPTIONS]";

$SDOC{update}{command} = <<EndCommand;

Check and pull the base repository. If the source files for the '{NAME}' have changed,
reinstall it.

Options are:
  
  --force      Install the command even if none of the source files have changed. Rebuild
               Makefile even if it is newer than the source.

EndCommand

$ADOC{update}{repos} = '[OPTIONS] [NAMES]';

$SDOC{update}{repos} = <<EndRepos;

If run without any arguments, pulls the base repository and then pulls all of the repos listed in
the file 'setup.yml' in the base directory. If you give one or more repository names or component
names, all repositories matching the argument will be pulled.

Unless the option --force is specified, a repository will be pulled only if it is on branch
'master' and there are no changes waiting to be committed. Any repository not meeting these
criteria will be skipped. If the source code for any container is updated as a result of a pull,
you will be asked if you want to rebuild it. If the rebuild fails, you may want to try pulling
the preload image for the container and trying again, because that may have changed as well.

You can specify one or more arguments on the command line, in which case just those repositories
whose path name or corresponding container name matches any of the arguments will be pulled. The
argument 'base' pulls just the base repository. The following options can also be specified:

  --force          Pull repositories even if they are on a branch other than 'master'
	           or have uncommitted changes. This is risky, because the pull might
                   leave the code in a non-runnable state. It is better to use 'git stash'
                   to temporarily set aside the changes and then run this command without
                   the '--force' option.

  --remote=URL     Pull from the specified URL, adding the name of the remote
	           repository as the last component.

  --verbose, -v    Print extra messages about the paths being checked by this command.

EndRepos

$ADOC{update}{config} = '[OPTIONS] [SECTION]';

$SDOC{update}{config} = <<EndConfig;

     or {NAME} update config [OPTIONS] file NAME

This command allows you to change the configuration settings stored in the main configuration
file. The values of some of these settings are also stored in other configuration files that are
used by the various components of this installation. These include database usernames and
passwords, the domain names under which various parts of the project are accessed, and other
similar values. Whenever you change these values, you will be asked if you wish to rebuild and
restart the affected services.

The configuration settings are numerous enough to be grouped into several different
sections. There is one section for each installed project component, plus a general configuration
section. When this step is executed as part of the initial install, the sections will be presented
one at a time. You will be asked for a value for each setting, and often an appropriate default
will be presented. To accept this default, just hit enter. When you execute the '{NAME} update
config' command, you can specify a section name. If you do not, it will run through all of the
installed sections.

Options for the first form of the command:

  --reset           Discard ALL configuration settings and ask again starting with the defaults.
                    This option should only be used as a last resort. To emphasize, all local
                    configuration settings you have previously specified will be lost, except
                    for the database root password.

Configuration sections:

  paleobiodb, pbdb    Settings for the paleobiodb project component, if installed
  macrostrat, macro   Settings for the macrostrat project component, if installed
  earthlife           Settings for the earthlife project component, if installed
  rockd               Settings for the rockd project component, if installed
  mibasin             Settings for the mibasin project component, if installed
  general             General settings


To use the second form of the command, the final arguments should be one or more strings that will
be matched against the names of configuration files and project components. You will be asked whether
to rebuild any files that match, using the current configuration settings. Without any options,
the file(s) you choose to rebuild will be rewritten to use the values from the main configuration
file, if any of them differ from the values in the current file.

Options for the second form of the command:

  --rebuild         Discard the existing content of any file that is to be rebuilt, and
                    recreate the file by substituting the current configuration settings
                    into a copy of the base file. If you previously made manual edits to
                    the file, your changes will be lost. If you wish to preserve them, use
                    the --merge option instead.

  --merge           Recreate any file that is to be rebuilt by substituting the current
                    configuration settings into a copy of the base file, and then merge that
                    content with the existing content. If incompatible changes are detected,
                    an editor window will be opened so that you can decide how to resolve
                    the conflict.

EndConfig

$ADOC{update}{images} = '[SERVICES]';

$SDOC{update}{images} = <<EndImages;

When run without any arguments, checks the container registry for updated preload images and pulls
any that it finds. The registry URL is listed in the configuration file under the key
'remote_registry'. The 'docker login' command will be run automatically at the beginning of this
step, and 'docker logout' afterward. You will be asked if you want any of the affected containers
rebuilt.

You can also specify one or more service names on the command line, in which case only the the
images corresponding to those containers will be checked. The following options are also
available:

  --registry=url    Use the specified registry URL, instead of the one listed in the config file.

EndImages

$ADOC{update}{database} = 'SUBCOMMAND';

$SDOC{update}{database} = <<EndDatabase;

 or update postgresql SUBCOMMAND
 or update mariadb SUBCOMMAND

Update one or more aspects of the database. You may specify a particular database component
to update, or else specify 'database' to update all components.

Subcommands are:

  volume               Delete THE ENTIRE CONTENT OF THE DATABASE and reinitialize it to an empty 
                       state.  Just to be extra clear, this will DESTROY ALL OF THE CONTENT
                       held by the specified database component(s) in this installation.

  content              Reload part or all of the database content. This subcommand is identical
                       to '{NAME} update content'. The database component name is ignored,
		       because it is overridden according to which content pieces you subsequently
                       specify.

  procedures [NAME]    Install or reinstall the stored procedures necessary for the API and other
                       services in this installation. If a component name or a database name is
		       specified, the stored procedures necessary for that database or all the
                       databases associated with that component are updated. If no arguments are
                       given, then all stored procedures are updated.

  schema [NAME]        Add or modify database columns as necessary to bring an old version of the
                       database content up to the current schema. If no database name or component
                       name is specified, all database schemas that this system knows about are
                       checked and updated.

  [ROLE] password      Change one or more of the database passwords used by this project. The
                       list of roles is given below. The database component name is ignored
                       for all passwords except 'root', because the same passwords are used
                       with all database components.

  [ROLE] user          Update the privileges granted to the api or exec user to match the set
                       expected and used by the latest version of this software. You will also
                       be given the option to change the username and/or password.

Database roles:

  root                 You can change the root password, but cannot change any other aspect of
                       the root database login. Each database management component has its own
                       root password.

  exec                 The executive database login allows you to view and make changes to all
                       of the databases, view running processes, and shut down the database.
                       The same executive password is used with all database management components.

  paleobiodb, pbdb     This password is used by the services of the paleobiodb component to access
                       their databases. It provides read/write access to all of the paleobiodb
                       databases, and read-only access to the macrostrat databases.
  
  macrostrat, macro    This password is used by the services of the macrostrat component to access
                       their databases. It provides read/write access to all of the macrostrat
                       databases, and read-only access to the paleobiodb databases.

  rockd                This password is used by the services of the rockd component to access their
                       databases. It provides read/write access to all of the rockd databases,
                       and read-only access to the macrostrat databases.

  mibasin              This password is used by the services of the mibasin component to access
                       their databases. It provides read/write to all of the mibasin databases,
                       and read-only access to the paleobiodb and macrostrat databases.

  api                  Use of this keyword will prompt you to update the passwords for all of the
                       above components that are present in the current installation.

EndDatabase

$ADOC{update}{postgresql} = 'SUBCOMMAND';

$SDOC{update}{postgresql} = $SDOC{update}{database};

$ADOC{update}{mariadb} = 'SUBCOMMAND';

$SDOC{update}{mariadb} = $SDOC{update}{database};

$ADOC{update}{password} = 'ROLE';

$SDOC{update}{password} = <<EndPassword;

        {NAME} update ROLE password

Change the password for one of the database roles used by this installation. You can specify the
word 'password' and the role in either order on the command line. Each role corresponds to a
database username and a password. To change the username for a role, use '{NAME} update config'.

Roles include:

  api         This login is used by the various APIs to access the database. It is also available
              to you to use via the command '{NAME} mysql' in case you want to insert, delete, or
              update database records. You will be asked if you want to rebuild each of the
              containers in which the associated username and password are stored. This role is
              equivalent to '{NAME}' when used with the current command.

  pbdb        Update the login used by the Paleobiology database APIs.

  macrostrat  Update the login used by Macrostrat database APIs.

  exec        This role has additional privileges for creating, dropping, and altering tables. It
              is available for you to use via the command '{NAME} mysql -E' in case you want to
              alter the database schema. It can also be used by scripts you write.

  root        This is the actual root password for the database. This role is available for you
              to use via the command '{NAME} mysql -R' in case you want to do administrative
              tasks or change privileges. It is suggested that you WRITE THE NEW PASSWORD DOWN
              immediately, because there is no way to recover it.

EndPassword

$ADOC{update}{content} = '[OPTIONS] [COMPONENTS]';

$SDOC{update}{content} = <<EndContent;

Reload part or all of the database content, either from a remote site or from local files.
You can specify one or more content components to load, from the lists below. If you do not
specify anything, you will be asked to choose from a menu. The default choice, which you
can select by hitting the enter key, will be read from the main configuration file. If you
choose something different, you will be asked if you want to make that the default from now
on. If you do not specify either of the options below, the choice of remote site or local file
will similarly be read from the configuration file.

Options:

  --auto, -y             For all questions, use the default answer from the configuration file.
                         This allows the process to proceed automatically using the stored defaults.

  --remote=url           Load the selected content from the specified remote site.

  --file=name            Load the selected content from a file or directory. This is only valid
                         if a single content component is selected.

  --set-default          Set the default for subsequent loads according to the components and options
                         given on the command line.

If you run this command as 'pbdb update content', you can specify one or more of the following
content components to load. The initial default will be 'master' for an installation that is configured
to be one of the official paleobiodb websites, and 'all' for other installations.

  pbdb              The database 'pbdb'
  pbdb_wing         The database 'pbdb_wing'
  database          Both 'pbdb' and 'pbdb_wing'
  images            The directory of images used on the website
  archives          The directory of saved data archives
  aux               Both 'images' and 'archives'
  macrostrat        The database 'macrostrat', used read-only by the Paleobiology Database
  all               All of the above
  datalogs          The directory of datalog files, only needed for the master site
  master            All of the above, including the datalogs

If you run this command as 'macrostrat update content', you can select from the following
content components to load. This list will expand in the future, as this command is refined for
use with macrostrat.

  macrostrat        The database 'macrostrat'
  all, master       All of the above

EndContent

$SDOC{update}{tasks} = <<EndTasks;

Start, stop, or change the automatic database maintenance tasks. These will vary depending
upon the purpose of this installation, so the defaults will vary depending upon the
configuration of this installation. For example, the main Paleobiology Database server
should execute nightly backups and sending of content to remote sites whereas other
installations of the Paleobiology Database do not need either task.

To change the configuration of this installation, execute '{NAME} update project'.

EndTasks

$SDOC{update}{website} = <<EndWebsite;

Change the website configuration. You will be asked the same series of questions as the
'website' install step. The webserver (nginx) container will be rebuilt and restarted when
you are done. This command makes it quite easy to modify the website configuration whenever
desired.

EndWebsite

sub UpdateCmd {

    @SAVE_ARGV = @ARGV;
    
    my $cmd = shift @ARGV;

    my $step;

    # Look for options before the update step name. We include common options here.

    my ($opt_verbose, $opt_force, $opt_merge, $opt_registry, $opt_origin,
	$opt_reset, $opt_all);
    
    Getopt::Long::Configure('permute');
    
    GetOptions( # 'quiet|q' => \$opt_quiet,
	       'verbose|v' => \$opt_verbose,
	       'force' => \$opt_force,
	       'merge' => \$opt_merge,
	       # 'check' => \$opt_check,
	       'all' => \$opt_all,
	       'origin=s' => \$opt_origin,
	       'registry=s' => \$opt_registry,
	       'reset' => \$opt_reset,
	       # 'nocolor' => \$opt_nocolor
	      );
    
    $step = shift @ARGV;
    
    die "ERROR: you must specify an update subcommand\n" unless $step;
    
    # Correct potential typographical errors and allow aliases.
    
    my $real_step = $UPDATE_ALIAS{$step} || $step;
    
    if ( $real_step eq 'setup' ) { unshift @ARGV, 'setup' };
    
    # if ( $step eq 'contents' ) { $step = 'content'; }
    # if ( $step eq 'code' || $step eq 'repo' || $step eq 'repos' ) { $step = 'codebase'; }
    
    # Create the options hash.
    
    my $options = { update => $step };
    
    $options->{verbose} = 1 if $opt_verbose;
    $options->{force} = 1 if $opt_force;
    $options->{merge} = 1 if $opt_merge;
    $options->{registry} = $opt_registry if $opt_registry;
    $options->{origin} = $opt_origin if $opt_origin;
    $options->{reset} = 1 if $opt_reset;
    $options->{all} = 1 if $opt_all;
    
    # Read the local configuration file in preparation for executing the specified update command.
    # If it is empty, warn the user. The user may execute 'update project' or 'update config' to
    # re-establish it.
    
    my $result = ReadLocalConfig({ empty_ok => 1, absent_ok => 1});
    
    unless ( $result )
    {
	if ( $real_step eq 'project' || $real_step eq 'config' )
	{
	    print "\nERROR: the main configuration file $LOCAL_CONFIG is missing.\n";
	    exit 2 unless AskQuestion("Do you want to re-establish this file from scratch?",
				  { yesno => 1 }) eq 'yes';

	    copy($DEFAULT{main_template}, $LOCAL_CONFIG) ||
		die "ERROR: could not copy $DEFAULT{main_template} to $LOCAL_CONFIG: $!\n";

	    print "\nCopying $DEFAULT{main_template} to $LOCAL_CONFIG.\n\n";
	}

	else
	{
	    print "ERROR: cannot proceed because the main configuration file $LOCAL_CONFIG is missing.\n";
	    exit 2;
	}
    }

    # Read the component data.
    
    ReadComponentData;
    
    # Set the umask for this process according to the file permissions chosen during the
    # configuration process. We have to flip bits to go from a filemode to a umask. If no filemode
    # was set, default to 0664 -> 0002.
    
    my $raw_perm = $CONFIG{file_permissions} || 'f0664';
    my $umask = substr($raw_perm, 2, 3);
    $umask =~ tr/640/027/;
    
    umask "0$umask";
    
    PrintDebug("umask 0$umask") if $DEBUG;
    
    # If there is either an update step or an install step corresponding to the argument, execute
    # it now.
    
    my $routine = $UPDATE_STEP{$real_step} || $INSTALL_STEP{$real_step};
    
    if ( $routine )
    {
	return &$routine( $options );
    }
    
    else
    {
	print "ERROR: '$step' is not an update subcommand\n";
	print "\nAvailable update subcommands are:\n";
	print "    $_\n" foreach @UPDATE_STEP;
	die "\n";
    }
}


# UpdateCodebaseCmd ( options )
#
# This command incorporates any changes to the project codebase, and also rebuilds any resources
# that are out of date.

sub UpdateCodebaseCmd {

    my ($options) = @_;
    
    # Options have already been parsed by &UpdateCmd, so we need to examine any remaining
    # command-line arguments.
    
    my $filter;
    
    while ( @ARGV )
    {
	my $arg = shift @ARGV;

	if ( $arg eq 'all' )
	{
	    $options->{all} = 1;
	}

	elsif ( $filter )
	{
	    print "ERROR: only one argument is allowed for 'update codebase'.\n";
	    exit 2;
	}

	else
	{
	    $filter = $arg;
	}
    }
    
    # Execute the update steps necessary in order to pull changes to the codebase and reflect
    # those changes in the configuration files.    
    
    if ( $filter eq 'base' )
    {
	$options->{restart} = 1;
	&CommandStep($options);
	&UpdateSetup($options, 'base');
    }
    
    elsif ( $filter eq 'setup' )
    {
	&UpdateSetup($options, 'setup');
    }
    
    elsif ( $filter )
    {
	&UpdateSetup($options, $filter);
	&CodebaseStep($options, $filter);
	&BuildStep($options);
    }
    
    else
    {
	$options->{restart} = 1;
	&CommandStep($options);
	&UpdateSetup($options);
	&CodebaseStep($options);
	&BuildStep($options);
    }

    print "\n";
}


# Step 1 [project] - decide which project component(s) to install

sub ProjectStep {
    
    my ($options) = @_;
    
    # Ask (or re-ask) for the basic project configuration. The first question is what file
    # permissions to use for the project files.
    
    my $gid = (stat($MAIN_PATH))[5];
    my $grname = (getgrgid($gid))[0] || $gid || '???';
    
    my $file_permissions = AskChoice("Who should have access to the files in this installation?",
				 { default => $CONFIG{file_permissions}, number_choices => 1, return_choice => 1 },
				     "f0644", "Writable by me, readable by everyone (0644)",
				     "f0640", "Writable by me, readable by group '$grname' (0640)",
				     "f0600", "Writable by me, readable by nobody else (0600)",
				     "f0664", "Writable by group '$grname', readable by everyone (0664)",
				     "f0660", "Readable and writable by group '$grname' (0660)");
    
    my $mode = substr($file_permissions, 1, 4);
    
    my $git_perm = $GIT_PERM{$file_permissions} || 'umask';
    
    SystemCommand("cd $MAIN_PATH; git config core.sharedRepository $git_perm");
    
    if ( $file_permissions ne $CONFIG{file_permissions} || $options->{reset} )
    {
	my $change_them = AskQuestion("Do you want to change the existing project files to reflect this? (y/n)",
				      { yesno => 1 });
	
	if ( $change_them eq 'yes' )
	{
	    local($DEBUG) = 1;

	    # $$$ must change core.sharedRepository in all repos
	    
	    # This may not change all of the files, because it will only affect those owned by the
	    # user running this command. Those owned by other users will need to be fixed
	    # manually. But certificates and other special files owned by root should be left
	    # under that ownership.
	    
	    my $chmod_arg = $CHMOD_MAP{$file_permissions};
	    SystemCommand('chmod', '-R', $chmod_arg, $MAIN_PATH) if $chmod_arg;	    
	}
    }
    
    # Set the umask for this process according to the file permissions chosen during the
    # configuration process. We have to flip bits to go from a filemode to a umask. If no filemode
    # was set, default to 0664 -> 0002.
    
    my $umask = substr($file_permissions, 2, 3);
    $umask =~ tr/640/027/;
    
    umask "0$umask";
    
    PrintDebug("umask 0$umask") if $DEBUG;
    
    # Then ask which component(s) should be included in this installation.
    
    my $include_paleobiodb;
    my $include_macrostrat;
    my $include_earthlife;
    my $include_rockd;
    my $include_mibasin;
    my $include_nginx = 'no';
    my $include_mariadb = 'no';
    my $include_postgresql = 'no';
    my $devel_configuration;
    
    my %required;
    
    my $project_choice = AskChoice("Select the component(s) for this installation:",
			       { default => $CONFIG{project_choice}, return_choice => 1 },
				   "1", "The Paleobiology Database *",
				   "2", "Macrostrat *",
				   "3", "Both Paleobiology Database and Macrostrat together *",
				   "4", "Earthlife only",
				   "5", "Rockd only",
				   "6", "Michigan Basin Fossils only");
    
    # If the paleobiodb is selected, ask whether to include the earthlife component
    # as well.
    
    if ( $project_choice eq "1" || $project_choice eq "3" )
    {
	$include_paleobiodb = 'yes';
	
	my @requirements = split /\s*,\s*/, $COMPONENT{paleobiodb}{requires};
	$required{$_} = 1 foreach @requirements;
 	
	$include_earthlife = AskQuestion("Include the Earthlife component as well?",
				     { default => $CONFIG{include_earthlife}, yesno => 1 } );
	
	if ( $include_earthlife eq 'yes' )
	{
	    my @requirements = split /\s*,\s*/, $COMPONENT{earthlife}{requires};
	    $required{$_} = 1 foreach @requirements;
	}
	
	if ( $project_choice eq "1" )
	{
	    $include_macrostrat = 'no';
	    $include_rockd = 'no';
	    $include_mibasin = 'no';
	}
    }
    
    # If macrostrat is selected, ask whether to include rockd and mibasin as well.
    
    if ( $project_choice eq "2" || $project_choice eq "3" )
    {
	$include_macrostrat = 'yes';
	
	my @requirements = split /\s*,\s*/, $COMPONENT{macrostrat}{requires};
	$required{$_} = 1 foreach @requirements;
	
	$include_rockd = AskQuestion("Include the Rockd component as well?",
				 { default => $CONFIG{include_rockd}, yesno => 1 });
	
	if ( $include_rockd eq 'yes' )
	{
	    my @requirements = split /\s*,\s*/, $COMPONENT{rockd}{requires};
	    $required{$_} = 1 foreach @requirements;
	}  
	
	$include_mibasin = AskQuestion("Include the Michigan Basin Fossils component as well?",
				   { default => $CONFIG{include_mibasin}, yesno => 1 });

	
	if ( $include_mibasin eq 'yes' )
	{
	    my @requirements = split /\s*,\s*/, $COMPONENT{mibasin}{requires};
	    $required{$_} = 1 foreach @requirements;
	}  
	
	if ( $project_choice eq "2" )
	{
	    $include_paleobiodb = 'no';
	    $include_earthlife = 'no';
	}
    }
    
    # The secondary-only installations can be used for development, or else to run one of the
    # component websites on a server than paleobiodb.org or macrostrat.org.
    
    if ( $project_choice eq "4" )
    {
	$include_paleobiodb = 'no';
	$include_earthlife = 'yes';
	$include_macrostrat = 'no';
	$include_rockd = 'no';
	$include_mibasin = 'no';
	my @requirements = split /\s*,\s*/, $COMPONENT{earthlife}{requires};
	$required{$_} = 1 foreach @requirements;
    }

    if ( $project_choice eq "5" )
    {
	$include_paleobiodb = 'no';
	$include_earthlife = 'no';
	$include_macrostrat = 'no';
	$include_rockd = 'yes';
	$include_mibasin = 'no';
	my @requirements = split /\s*,\s*/, $COMPONENT{rockd}{requires};
	$required{$_} = 1 foreach @requirements;
    }

    if ( $project_choice eq "6" )
    {
	$include_paleobiodb = 'no';
	$include_earthlife = 'no';
	$include_macrostrat = 'no';
	$include_rockd = 'no';
	$include_mibasin = 'yes';
	my @requirements = split /\s*,\s*/, $COMPONENT{mibasin}{requires};
	$required{$_} = 1 foreach @requirements;
    }
    
    # Inform the user of additional components that are required by the selected components.

    if ( $required{nginx} || $required{mariadb} || $required{postgresql} )
    {
	print "\nThe following services will also be included, because the components you\n";
	print "selected depend on them:\n\n";
	
	if ( $required{nginx} )
	{
	    print "    nginx\n";
	    $include_nginx = 'yes';
	}

	if ( $required{mariadb} )
	{
	    print "    mariadb\n";
	    $include_mariadb = 'yes';
	}

	if ( $required{postgresql} )
	{
	    print "    postgresql\n";
	    $include_postgresql = 'yes';
	}
    }
    
    # Ask if this installation should be configured for software development. This option adds
    # extra volume mounts to docker-compose.yml, so that changes to source files are immediately
    # visible in containers. It may also change the contents of certain configuration files,
    # although as of the time this comment was written no such changes had been implemented.

    $devel_configuration = AskQuestion("Configure this installation for software development?",
				   { default => $CONFIG{devel_configuration}, yesno => 1 });
    
    # If any component is to be removed, reconfirm this choice.
    
    if ( $CONFIG{include_paleobiodb} eq 'yes' && $include_paleobiodb eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Paleobiology Database " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of paleobiodb component.\n";
	    $include_paleobiodb = 'yes';
	}
    }
    
    if ( $CONFIG{include_earthlife} eq 'yes' && $include_earthlife eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Earthlife " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of earthlife component.\n";
	    $include_earthlife = 'yes';
	}
    }
    
    if ( $CONFIG{include_macrostrat} eq 'yes' && $include_macrostrat eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Macrostrat " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of macrostrat component.\n";
	    $include_macrostrat = 'yes';
	}
    }
    
    if ( $CONFIG{include_rockd} eq 'yes' && $include_rockd eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Rockd " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of rockd component.\n";
	    $include_rockd = 'yes';
	}
    }
    
    if ( $CONFIG{include_mibasin} eq 'yes' && $include_mibasin eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Michigan Basin Fossils " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of mibasin component.\n";
	    $include_mibasin = 'yes';
	}
    }
    
    if ( $CONFIG{include_nginx} eq 'yes' && $include_nginx eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE Nginx " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of nginx component.\n";
	    $include_nginx = 'yes';
	}
    }
    
    if ( $CONFIG{include_mariadb} eq 'yes' && $include_mariadb eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE MariaDB " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of mariadb component.\n";
	    $include_mariadb = 'yes';
	}
    }
    
    if ( $CONFIG{include_postgresql} eq 'yes' && $include_postgresql eq 'no' )
    {
	unless ( AskQuestion("Please confirm: do you want to REMOVE PostgreSQL " .
			     "from this installation?",
			 { default => 'no', yesno => 1 }) )
	{
	    print "\nCanceled removal of postgresql component.\n";
	    $include_postgresql = 'yes';
	}
    }
    
    # Save these choices to the local configuration file.
    
    print "\nSaving changes to config.yml...\n";
    
    RewriteLocalConfig({ file_permissions => $file_permissions,
			 devel_configuration => $devel_configuration,
			 project_choice => $project_choice,
			 include_paleobiodb => $include_paleobiodb,
			 include_macrostrat => $include_macrostrat,
			 include_earthlife => $include_earthlife,
			 include_rockd => $include_rockd,
			 include_mibasin => $include_mibasin,
			 include_nginx => $include_nginx,
			 include_mariadb => $include_mariadb,
			 include_postgresql => $include_postgresql,
		       }, $options);
    
    # Clear the component data, and then reload it using the new include_* settings just written.
    
    %COMPONENT = ();
    
    ReadComponentData;
    
    # If setup.override.yml doesn't exist, establish it by copying project/setup.override.yml.
    
    # my $local_setup = $CONFIG{local_setup} || 'setup.yml';
    
    EnsureFile($CONFIG{local_setup}, $SETUP_OVERRIDE_BASE) if $CONFIG{local_setup};
    
    # If docker-compose.override.yml doesn't exist, establish it by copying 
    # project/docker-compose.override.yml.
    
    EnsureFile($LOCAL_COMPOSE, $COMPOSE_OVERRIDE_BASE);
    
    # If project-data.override.yml doesn't exist, establish it by copying
    # project/docker-compose.override.yml.
    
    EnsureFile($CONFIG{local_component_data}, $COMPONENT_OVERRIDE_BASE) if $CONFIG{local_component_data};
    
    # Then generate (or re-generate) the master setup and compose files.
    
    UpdateSetup($options);
}


# UpdateSetup ( options )
# 
# Generate the files setup.yml, docker-compose.yml, and frontend/nginx/Dockerfile from template
# files, by selecting only the sections corresponding to installed project components. The resulting
# files should not be edited manually, because any change in the project configuration or change
# in the template files will cause the edits to be overwritten.
# 
# Any manual changes to the setup should instead be added to setup.override.yml and/or
# docker-compose.override.yml.

sub UpdateSetup {
    
    my ($options, $filter) = @_;

    my $exit_after_rebuild;
    
    # For each installed project component, fetch the git repository if it has not already been
    # installed.
    
    my $component_updated;
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	unless ( $COMPONENT{$component}{main_repo} )
	{
	    if ( ! $filter || $filter eq $component )
	    {
		my $origin = $COMPONENT{$component}{origin};
		my $path = $COMPONENT{$component}{path};
		my $no_clone;
		
		if ( -e $path && -e "$path/.git" )
		{
		    GitRefresh($path, $options) && $component_updated++;
		    $no_clone = 1;
		}
		
		elsif ( -e $path )
		{
		    my $path_contents = `ls $path`;
		    
		    if ( $path_contents =~ /\w/ )
		    {
			my $answer = AskQuestion(" > Replace the content at $path with " .
						 "git repository $origin? (y/n/q)",
					     { yesnoquit => 1, default => 'yes' });
			
			exit if $answer eq 'quit';

			if ( $answer eq 'yes' )
			{
			    SystemCommand("rm -rf $path");
			    make_path($path, 1);
			}

			else
			{
			    $no_clone = 1;
			}
		    }
		}
		
		unless ( $no_clone )
		{
		    GitClone($path, $options, $origin);
		    $component_updated++;
		}
	    }
	}
    }
    
    # If any components were updated, clear the component data and reload it to incorporate any
    # changes that might have been made to the component-data.yml file in the component's
    # repository.

    if ( $component_updated )
    {
	print "\n - RELOADING component data\n";
	
	%COMPONENT = ();
	
	ReadComponentData;
    }
    
    # Now tell the user which components we think are installed in the system. 
    
    my $component_list = join(', ', @INSTALLED_COMPONENTS) || 'none';
    
    $component_list .= " with development configuration" if $CONFIG{devel_configuration} eq 'yes';
    
    print "\n - GENERATING configuration files for: $component_list\n";
    
    # The file docker-compose.yml is generated from project/docker-compose-template.yml and the
    # list of selected project components. If this installation is to be configured for software
    # development, the additional sections in @dev_list are also included.
    
    die "ERROR: 'main_compose_template' is not defined.\n" unless $CONFIG{main_compose_template};
    die "ERROR: 'component_compose_template' is not defined.\n" unless $CONFIG{component_compose_template};
    
    my $generate_compose = $options->{force} || $options->{install} || ! -e $MASTER_COMPOSE;
    
    my %template_filename = ListComponentTemplates($CONFIG{component_compose_template});
    
    unless ( $generate_compose )
    {
	$generate_compose = CheckTemplateTarget($MASTER_COMPOSE, $options->{ask},
						$CONFIG{main_compose_template},
						values %template_filename);
	
	exit if $generate_compose && $generate_compose eq 'quit';
    }
    
    if ( $generate_compose )
    {
	my $compose_sections = { };
	
	# Read in all of the template files.
	
	ReadTemplate($compose_sections, $CONFIG{main_compose_template}, 'header');
	
	foreach my $component ( @INSTALLED_COMPONENTS )
	{
	    if ( $template_filename{$component} )
	    {
		ReadTemplate($compose_sections, $template_filename{$component}, $component);
	    }
	}
	
	# Not all components may have corresponding sections in the compose file.

	my @compose_list = grep { $compose_sections->{$_} } @INSTALLED_COMPONENTS;
	
	my @dev_list = grep { $compose_sections->{$_} } map { "$_-dev" } @INSTALLED_COMPONENTS;
	
	# If the value of the configuration setting 'letsencrypt_path' is an existing directory,
	# include a separate section that mounts that directory into the nginx container. This
	# will allow the use of certbot to obtain and renew certificates. If that setting hasn't
	# been set yet (which will happen during an initial install) also check the two possible
	# paths for that directory that we know about.
	
	my $check1 = "/etc/letsencrypt";
	my $check2 = "/opt/local/etc/letsencrypt";
	
	if ( -d $CONFIG{letsencrypt_path} || -d $check1 || -d $check2 )
	{
	    push @compose_list, 'letsencrypt';

	    $CONFIG{letsencrypt_path} ||= $check1 if -d $check1;
	    $CONFIG{letsencrypt_path} ||= $check2 if -d $check2;
	}
	
	# If the setting 'devel_configuration' is true, add the development sections to the list.

	if ( $CONFIG{devel_configuration} eq 'yes' )
	{
	    push @compose_list, @dev_list;
	}
	
	# If any services are running, do a dry run on generating the new compose file. If
	# it is going to change, the running services must be taken down first.
	
	if ( -e $MASTER_COMPOSE && GetRunningServices() )
	{
	    # The ~ on the end of the target file name is a hack to indicate that we are only
	    # checking and not actually rebuilding the file.
	    
	    my $updated = GenerateYAMLFromTemplate("$MASTER_COMPOSE~", $compose_sections, { },
						   'header', @compose_list);
	    
	    if ( $updated )
	    {
		print "\nAll running services must be taken down before rebuilding $MASTER_COMPOSE.\n";
		print "This update will be aborted if you answer no.\n";
		
		my $answer = AskQuestion(" > Stop all running services and remove their containers? (y/n/q)",
				     {yesnoquit => 1, default => 'yes' });
		
		if ( $answer eq 'yes' )
		{
		    SystemDockerCompose('down');
		    print "\n";
		}
		
		else
		{
		    print "\nAborting.\n";
		    exit;
		}
	    }
	}
	
	# Now generate the new file contents.
	
	my $updated = GenerateYAMLFromTemplate($MASTER_COMPOSE, $compose_sections, { },
					       'header', @compose_list);
	
	# Run 'docker-compose config' to make sure that the file contents are correct. If
	# something is wrong, the command will generate no output. If it does generate YAML
	# output, we check to make sure it has both 'services' and 'volumes' as top-level keys.	
	
	my $output = CaptureCommand("docker-compose", "config");
	
	if ( $output && $output =~ /^services:/m &&
		 $output =~ /^\s*volumes:/m && $output =~ /^\s*ports:/m )
	{
	    # If the contents are correct, remove any .error file because we no longer need it after
	    # the contents have been validated.
	    
	    if ( $updated )
	    {
		if ( -e "$MASTER_COMPOSE.error" )
		{
		    PrintDebug("unlink $MASTER_COMPOSE.error") if $DEBUG;
		    unlink("$MASTER_COMPOSE.error");
		}
		
		# Now create or recreate the .services file by calling GetComposeServices.
		
		my @service_list = GetComposeServices();
	    }
	}
	
	# If the new contents are not correct, restore the old version if one exists and print out
	# an error message to the user.
	
	else
	{
	    print "ERROR: the newly generated contents of $MASTER_COMPOSE are invalid.\n";
	    
	    if ( $options->{install} )
	    {
		print "\nSomething has gone very wrong. You will need to fix this problem and\n";
		print "then re-run install.pl.\n\n";
		exit 2;
	    }
	    
	    elsif ( $updated && -e "$MASTER_COMPOSE.bak" )
	    {
		print "Saving bad file as $MASTER_COMPOSE.error\n";
		PrintDebug("rename $MASTER_COMPOSE => $MASTER_COMPOSE.error") if $DEBUG;
		rename($MASTER_COMPOSE, "$MASTER_COMPOSE.error");
		print "Restoring old version\n";
		PrintDebug("rename $MASTER_COMPOSE.bak => $MASTER_COMPOSE") if $DEBUG;
		rename("$MASTER_COMPOSE.bak", $MASTER_COMPOSE);
	    }

	    print "\n";
	}
    }

    else
    {
	print "\n - FILE $MASTER_COMPOSE is up to date\n";
    }
    
    # The file setup.yml is generated from project/setup-template.yml and the list of selected
    # project components.
    
    die "ERROR: 'master_setup' is not defined\n" unless $CONFIG{master_setup};
    die "ERROR: 'main_setup_template' is not defined\n" unless $CONFIG{main_setup_template};
    die "ERROR: 'component_setup_template' is not defined\n" unless $CONFIG{component_setup_template};
    
    my $generate_setup = $options->{force} || $options->{install} || ! -e $CONFIG{master_setup};
    
    %template_filename = ListComponentTemplates($CONFIG{component_setup_template});
    
    unless ( $generate_setup )
    {
	$generate_setup = CheckTemplateTarget($CONFIG{master_setup}, $options->{ask},
					      $CONFIG{main_setup_template},
					      values %template_filename);
	
	exit if $generate_compose && $generate_compose eq 'quit';
    }
    
    if ( $generate_setup )
    {
	my $setup_sections = { };

	# Read in all of the template files.

	ReadTemplate($setup_sections, $CONFIG{main_setup_template}, 'header');

	foreach my $component ( @INSTALLED_COMPONENTS )
	{
	    if ( $template_filename{$component} )
	    {
		ReadTemplate($setup_sections, $template_filename{$component}, $component);
	    }
	}
	
	# Now generate the new file contents.
	
	my $updated = GenerateYAMLFromTemplate($CONFIG{master_setup}, $setup_sections, { },
					       'header', @INSTALLED_COMPONENTS);
	
	# Do a simple check of the file contents, even if they didn't change.
	
	my $check = ReadConfigFile($CONFIG{master_setup}, { no_cache => 1 });
	
	if ( $check && $check->{setup} && ref $check->{setup} eq 'ARRAY' &&
	     @{$check->{setup}} > 2 )
	{
	    # If the contents have changed, note this so that the rest of the installation can be
	    # checked and adjusted to match.
	    
	    if ( $updated )
	    {
		$setup_file_changed = 1;
	    }
	    
	    # # Delete the .bak file, because we no longer need it.

	    # if ( -e "$MASTER_SETUP.bak" )
	    # {
	    # 	PrintDebug("unlink $MASTER_SETUP.bak") if $DEBUG;
	    # 	unlink("$MASTER_SETUP.bak");
	    # }
	}
	
	# If the new contents are not correct, restore the old version if one exists and print out
	# an error message to the user.
	
	else
	{
	    print "ERROR: the newly generated contents of $CONFIG{master_setup} are invalid.\n";
	    
	    if ( $options->{install} )
	    {
		print "\nSomething has gone very wrong. You will need to fix this problem and\n";
		print "then re-run install.pl.\n\n";
		exit 2;
	    }
	    
	    if ( $updated && -e "$CONFIG{master_setup}.bak" )
	    {
		print "Restoring old version.\n";
		PrintDebug("rename $CONFIG{master_setup}.bak => $CONFIG{master_setup}") if $DEBUG;
		rename("$CONFIG{master_setup}.bak", $CONFIG{master_setup});
	    }

	    print "\n";
	}
    }
    
    else
    {
	print "\n - FILE $CONFIG{master_setup} is up to date\n";
    }
    
    # The file frontend/nginx/Dockerfile is generated from frontend/nginx/Dockerfile-template and
    # the list of selected project components.
    
    # If the option 'ask' was given, check to see if the template file is newer than the
    # target. If it is, ask the user if they want to regenerate the target. If no option was
    # given, generate the file regardless.

    my $mode = '';

    $mode = 'ask' if $options->{ask};
    $mode = 'force' if $options->{force} || $options->{install};
    
    BuildNginxDockerfile($mode);
}


# ShowComponentsCmd ( )
#
# List the active project components.

sub ShowComponentsCmd {

    my ($options) = @_;
    
    if ( $ARGV[0] )
    {
	print "Unknown argument '$ARGV[0]'.\n";
    }
    
    # my $data_file = $CONFIG{project_data} || 'project/project-data.yml';
    
    # my $project_data = ReadConfigFile($data_file) || die "ERROR: could not read $data_file";
    
    # $project_data = $COMPONENT || die "could not find key 'component' in $data_file\n";
    
    my (@components, @sites, @domains);
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	if ( $COMPONENT{$component}{website} )
	{
	    my $site = $CONFIG{"site_$component"} || 'local';
	    my $domain = $site && $COMPONENT{$component}{website}{$site};
	    
	    push @components, $component;
	    push @sites, $site;
	    push @domains, $domain;
	}
	
	else
	{
	    push @components, $component;
	    push @sites, '-';
	    push @domains, '-';
	}
    }
    
    PrintOutputList($options, ['Project component', 'Site', 'Domain'],
		    \@components, \@sites, \@domains);
}

# Step 2 [codebase] install the necessary project components and the command.

sub CodebaseStep {
    
    my ($options, $filter) = @_;
    
    my $string = $filter ? " for '$filter'" : "";
    print "\nChecking installed codebase$string...\n";
    
    # Create the volumes directory unless it exists and is writable.
    
    my $volumes_dir = $CONFIG{volumes_dir};
    
    die "ERROR: volumes_dir is not defined\n" unless $CONFIG{volumes_dir};
    
    if ( -e $volumes_dir )
    {
	unless ( -w $volumes_dir )
	{
	    print "\n - CHOWN $<: $volumes_dir\n";
	    SystemCommand("sudo chown $<: $volumes_dir");
	}
    }
    
    else
    {
	print "\n - MKDIR $volumes_dir\n";
	make_path($volumes_dir);
    }
    
    # Keep track of whether any repositories failed to be created.
    
    my (@repos_failed, %container_failed);
    
    # Read setup information in YAML format from the master setup file and the local setup
    # file. The 'verbose' option indicates that error messages should be produced for any formatting
    # errors that are noticed rather than ignoring any that are not disabling.
    
    my @setup_list = ReadSetupFiles({ verbose => 1 });
    
    # Now go through all of the setup actions. If the action is invalid, print a warning and skip
    # it. Otherwise, carry it out.
    
    my %action_done;
    
 ENTRY:
    foreach my $entry (@setup_list)
    {
	my $path = $entry->{path};
	my $type = $entry->{type} || '';
	my $source = $entry->{source} || '';
	my $component = $entry->{component} || $entry->{project} || '';
	my $rename_from = $entry->{'rename-from'};
	
	# If a filter was given, skip all entries except those whose project or path matches the filter.
	
	if ( $filter )
	{
	    next unless $component eq $filter || $path =~ /$filter/;
	}
	
	# If this action has a 'rename-from' attribute and the rename-from path exists but the
	# regular path does not, then carry out the rename. If it fails, skip this entry.
	
	if ( $rename_from && -e $rename_from )
	{
	    print "\n - RENAME $rename_from => $path\n";
	    
	    if ( -e $path )
	    {
		print "    ERROR: could not rename $rename_from to $path: already exists\n";
		next ENTRY;
	    }
	    
	    elsif ( ! move($rename_from, $path ) )
	    {
		print "    ERROR: could not rename $rename_from to $path: $!\n\n";
		next ENTRY;
	    }
	}
	
	# Otherwise execute the action according to the type. A 'skip' action is just skipped.
	
	if ( $type eq 'skip' )
	{
	    print "\n - SKIP $path\n" if $DEBUG;
	    next ENTRY;
	}
	
	# A 'repository' action specifies a git repository. If it does not exist, it will be
	# cloned from the specified origin into the specified directory. If it is already there,
	# it will be checked and pulled if appropriate.
	
	elsif ( $type eq 'repository' )
	{
	    # Figure out which containers the repository is a source for. The 'container'
	    # attribute can either be a single name or a comma-separated list.
	    
	    my @container;
	    
	    if ( $entry->{container} )
	    {
		@container = split /\s*,\s*/, $entry->{container};
	    }
	    
	    # If the directory looks like a git repo, refresh it unless it was already refreshed above.
	    
	    if ( -e "$path/.git" )
	    {
		if ( ! $repo_checked{$path} )
		{
		    # If GitRefresh returns true, that means that changes were pulled.
		    
		    if ( GitRefresh($path, $options) )
		    {
			# If this repository has a 'container' attribute, flag all listed container
			# names as needing to be rebuilt.
			
			$rebuild_container{$_} = 1 foreach @container;
		    }
		}
	    }
	    
	    # Otherwise, we need to figure out the origin repository to clone from. The setup
	    # entry will generally specify only the last segment of the repository URL. In that
	    # case, it will be appended to the base origin URL for the component that contains
	    # this repository.
	    
	    else
	    {
		my $origin = $entry->{origin} || $entry->{remote};
		
		# If $origin is not empty but does not contain a colon ':', that means it is not a
		# full URL.
		
		if ( $origin && $origin !~ qr{ : }xs )
		{
		    # If we can determine the component with which this entry is associated, we
		    # use its origin URL as a base. We take everything up to the final slash and
		    # append the string specified as the repository origin.
		    
		    my $component = $entry->{component} || $entry->{project};
		    
		    if ( $component && 
			 $COMPONENT{$component}{origin} &&
			 $COMPONENT{$component}{origin} =~ qr{ ^ ( [^/]+ [/] ) }xs )
		    {
			$origin = $1 . $origin;
		    }
		    
		    # If this is not possible, print an error message and mark all of the
		    # associated containers as failed.
		    
		    else
		    {
			$component ||= '';
			
			print "\n - REPOSITORY [ERROR] $path could not be cloned\n";
			print "    ERROR: no origin found for '$component'\n";
			
			$container_failed{$_} = 1 foreach @container;
		    }
		}
		
		# If GitClone returns true, that means the repository was successfully
		# downloaded.
		
		if ( GitClone($path, $options, $origin) )
		{
		    # If this repository has a 'container' attribute, flag all listed container
		    # names as needing to be rebuilt.
		    
		    $rebuild_container{$_} = 1 foreach @container;
		}
		
		# Otherwise, we need to add this to the list of failed repositories and flag all
		# of the associate containers as failed too.
		
		else
		{
		    $origin ||= 'no origin was specified';
		    push @repos_failed, "    $path    $origin\n";
		    
		    $container_failed{$_} = 1 foreach @container;
		}
	    }
	}
	
	# A 'symlink' action makes a symlink, unless it is already there.
	
	elsif ( $type eq 'symlink' )
	{
	    MakeSymlink($entry, $options->{verbose});
	    
	    # my $target = $entry->{target};
	    
	    # unless ( $target )
	    # {
	    # 	print "WARNING: skipping symlink '$path' from $source: no target specified\n";
	    # 	next ENTRY;
	    # }
	    
	    # MakeSymlink($path, $target, $options->{verbose});
	}
	
	# A 'dir' action makes a directory, unless it is already there.
	
	elsif ( $type eq 'dir' )
	{
	    MakeDir($entry, $options->{verbose});
	    
	    # next ENTRY if $options->{check};
	    
	    # MakeDir($path, $entry->{chmod}, $options->{verbose});
	}
	
	# All other action types are invalid.
	
	else
	{
	    print "\n - SKIP $path from $source:\n    ERROR: type '$type' is not valid\n";
	}
    }

    # After we have gone through all of the entries, see if any of the listed repositories failed
    # to install.
    
    if ( @repos_failed )
    {
	print "\nWARNING: the following repositories could not be installed:\n\n";
	print @repos_failed;

	if ( %container_failed )
	{
	    my $list = join(', ', keys %container_failed);
	    print "\nThe following containers will not build: $list\n\n";
	}
	
	print "\nYou must install these repositories manually, or else fix the problem and\n";
	print "re-run this command.\n";
	
	my $response = AskQuestion("Continue? (y/n)", { yesnoquit => 1 });

	exit unless $response eq 'yes';
    }
    
    # Now install the command, or reinstall it if it any of the source files have changed.

    CommandStep($options);
    
    print "\n";
}


# MakeSymlink ( entry, verbose )
#
# The entry should be a hashref with attributes 'path' and 'target'. If 'path' is not symlinked to
# 'target', make it so.

sub MakeSymlink {

    my ($entry, $verbose) = @_;
    
    my $path = $entry->{path};
    my $target = $entry->{target};

    unless ( $target )
    {
	print "\n - SYMLINK [BAD ENTRY] $path => ???\n    ERROR: no link target specified\n";
	return;
    }
    
    if ( -l $path && readlink($path) eq $target )
    {
	print "\n - SYMLINK OK $path => $target\n" if $verbose;
	return 1;
    }
    
    elsif ( -l $path && ! unlink($path) )
    {
	print "\n - SYMLINK [WRONG TARGET] $path => $target\n    ERROR: could not update symlink: $!\n";
	return;
    }	
    
    elsif ( -e $path )
    {
	print "\n - SYMLINK [CONFLICT] $path => $target\n    ERROR: existing file or directory\n";
	return;
    }
    
    print "\n - SYMLINK CREATE $path => $target\n";
    
    if ( symlink($target, $path) )
    {
	return 1;
    }
    
    else
    {
	print "    ERROR: $!\n";
	return;
    }
}


sub MakeDir {

    my ($entry, $verbose) = @_;

    my $path = $entry->{path};
    my $mode = $entry->{mode};
    
    if ( -d $path && -w $path )
    {
	print "\n - DIRECTORY OK $path\n" if $verbose;
	return 1;
    }
    
    elsif ( -d $path )
    {
	print "\n - DIRECTORY [ERROR] $path\n    ERROR: directory is not writable\n";
	return;
    }
    
    elsif ( -e $path )
    {
	print "\n - DIRECTORY [CONFLICT] $path\n    ERROR: existing file or symlink\n";
	return;
    }
    
    my $message = $mode ? " with mode $mode" : "";
    
    print "\n - DIRECTORY CREATE $path$message\n";
    
    if ( ! make_path($path) )
    {
	print "    ERROR: $!\n";
	return;
    }
    
    if ( $mode && ! SystemCommand("chmod", $mode, $path) )
    {
	print "    ERROR: could not chmod $mode\n";
	return;
    }
	
    return 1;
}


# GitRefresh ( dir, options )
# 
# Check the status of the git repository at the path specified by the first argument. If it is on
# branch 'master' and there are no uncommitted changes, pull from origin/master.

sub GitRefresh {

    my ($path, $options) = @_;
    
    $repo_checked{$path} = 1;
    
    # Check to make sure this repository is writable by the user running this command.
    
    unless ( -d $path && -w $path && -w "$path/.git" )
    {
	print "\n - REPOSITORY [ERROR] $path could not e updated\n    ERROR: repository is not writable\n";
	return;
    }
    
    # Get the current status of this repository.
    
    my $status = CaptureCommand("cd $path; git status -b --porcelain");
    
    my ($branch, $filestatus, $uncommitted, $ahead, $repostate, $noupdate);
    
    my @lines = split /[\n\r]+/, $status;
    
    if ( $lines[0] =~ /^## ([^.]+)/ )
    {
	$branch = $1;
    }
    
    if ( $lines[1] =~ /^(..)/ )
    {
	$filestatus = $1;
    }
    
    if ( $lines[0] =~ /\[ahead (\d+)\]/ )
    {
	$ahead = $1;
    }
    
    unless ( @lines == 1 || $filestatus eq '??' || $filestatus eq '!!' )
    {
	$uncommitted = 1;
    }
    
    # Determine whether or not the repository can be updated.
    
    if ( ! $branch )
    {
	$repostate = "branch cannot be determined";
	$noupdate = 1;
    }
    
    elsif ( $branch ne 'master' && $branch ne 'dev' && ! $options->{force} )
    {
	$repostate = "is on branch '$branch'";
	$repostate .= " with uncommitted changes" if $uncommitted;
	$noupdate = 1;
    }
    
    elsif ( $uncommitted && ! $options->{force} )
    {
	$repostate = "has uncommitted changes";
	$noupdate = 1;
    }

    elsif ( $branch eq 'dev' )
    {
	$repostate = "is on branch 'dev'";
    }
    
    # If we are unable to update this repository, or if the option 'nopull' was given, do a dry
    # run and report whether anything would be pulled. Unless the option 'verbose' was given, do
    # not print anything for a repository that is on the master branch and is up to date.
    
    if ( $noupdate || $options->{nopull} )
    {
	$branch ||= 'master';
	
	my $check = CaptureCommand("cd $path; git fetch --dry-run origin $branch 2>&1");
	
	if ( $check =~ qr{ ( [0-9a-f]+ [.][.] [0-9a-f]+ ) }xs )
	{
	    my $message = $repostate ? "$repostate and REMOTE IS AHEAD" : "REMOTE IS AHEAD";
	    
	    print "\n - REPOSITORY [CHECK] $path $message\n";
	}

	elsif ( $noupdate || $branch eq 'dev' )
	{
	    print "\n - REPOSITORY [CHECK] $path $repostate\n";
	}

	elsif ( $options->{verbose} )
	{
	    print "\n - REPOSITORY [CHECK] $path is UP TO DATE\n";
	}

	return;
    }
    
    # Otherwise, pull the repository.
    
    else
    {
	$branch ||= 'master';
	
	my $output = CaptureCommand("cd $path; git pull origin $branch 2>&1");
	
	if ( $output =~ /^unpacking objects/mi )
	{
	    print "\n - REPOSITORY PULL $path\n";
	    print $output;
	    return 1;
	}
	
	elsif ( $output !~ /up[- ]to[- ]date/i )
	{
	    print "\n - REPOSITORY [BAD OUTPUT] $path\n";
	    print $output;
	}
	
	elsif ( $options->{verbose} || $options->{install} )
	{
	    print "\n - REPOSITORY OK $path is up to date\n";
	}

	return;
    }
}


# GitClone ( path, options, remote )
#
# Clone the specified remote repository to the specified local directory.

sub GitClone {

    my ($path, $options, $origin) = @_;
    
    $repo_checked{$path} = 1;
    
    unless ( $origin )
    {
	print "\n - REPOSITORY [ERROR] $path could not be cloned\n";
	print "    ERROR: no origin was specified for this repository\n";
	return;
    }

    unless ( $origin =~ qr{ : }xs )
    {
	print "\n - REPOSITORY [ERROR] $path could not be cloned\n";
	print "    ERROR: invalid origin '$origin'\n";
	return;
    }
    
    unless ( -e $path || make_path($path, 1) )
    {
	print "\n - REPOSITORY [ERROR] $path could not be cloned\n";
        print "    ERROR: could not create directory '$path': $!\n";
	return;
    }

    unless ( -w $path )
    {
	print "\n - REPOSITORY [ERROR] $path could not be cloned\n";
        print "    ERROR: directory is not writable\n";
	return;
    }
    
    my $path_contents = `ls $path`;
    
    if ( $path_contents =~ /\w/ )
    {
	my $answer = AskQuestion("\n > The directory $path exists and is not empty. Remove it and its contents?",
			     { yesno => 1 });
	
	unless ( $answer eq 'yes' )
	{
	    my $cmd = $options->{install} ? 'install.pl' : "'$COMMAND update'";
	    print "\n - REPOSITORY [CONFLICT] $path could not be cloned\n";
	    print "    ERROR: you must rename or remove the existing directory and then re-run $cmd\n";
	    return;
	}
	
	SystemCommand("rm -rf $path");
	make_path($path, 1);
	
	unless ( -w $path )
	{
	    print "\n - REPOSITORY [ERROR] $path\n";
	    print "    ERROR: could not create directory or directory not writable\n";
	    return;
	}
    }
    
    $MAIN_GROUP ||= (stat($MAIN_PATH))[5];
    SystemCommand("chgrp $MAIN_GROUP $path");
    
    print "\n - REPOSITORY CLONE $path FROM $origin\n";

    my @options;
    
    if ( $CONFIG{file_permissions} )
    {
	my $git_perm = $GIT_PERM{$CONFIG{file_permissions}} || 'umask';
	push @options, '--config', "core.sharedRepository=$git_perm";
    }
    
    if ( SystemCommand('git', 'clone', @options, $origin, $path) )
    {
	return 1;
    }
    
    else
    {
	my $cmd = join(' ', 'git', 'clone', @options, $origin, $path);
	print "    ERROR: the command '$cmd' failed\n";
	return;
    }
}


# CommandStep ( )
#
# Install the status and maintenance command if this is an install, or update it if any of the
# files have changed.

sub CommandStep {

    my ($options) = @_;
    
    # We first try pulling the main git repository, which includes the files for this command,
    # in case it has been updated since the repository was cloned or last pulled.
    
    GitRefresh($MAIN_PATH, { ask => ! $options->{all} });
    
    # Next, we create the file Path.pm unless it already exists and specifies the correct
    # path. Its sole reason for existence is to store the directory path where this installation
    # lives.
    
    CreatePathFile();
    
    # Make sure that the proper command names exist in the 'scripts' directory.
    
    my $force_makefile;
    
    if ( $CONFIG{include_macrostrat} )
    {
	unless ( -e "command/script/macrostrat" )
	{
	    symlink("pbdb", "command/script/macrostrat") ||
		print "ERROR: could not symlink command/script/macrostrat => pbdb: $!\n";
	    $force_makefile = 1;
	}
    }
    
    # Make sure that the Install_*.pm files are properly symlinked into the 'PMCmd' directory, or
    # are removed if they no longer exist.
    
    foreach my $component ( keys %COMPONENT )
    {
	my $path = $COMPONENT{$component}{path};
	my $sourcefile = "$path/component/Install_${component}.pm";
	my $commandfile = "command/lib/PMCmd/Install_${component}.pm";
	
	if ( -e $sourcefile && ! -e $commandfile )
	{
	    symlink("../../../$sourcefile", $commandfile) ||
		print "ERROR: could not symlink $commandfile => $sourcefile: $!\n";
	    $force_makefile = 1;
	}
	
	elsif ( -e $commandfile && ! -e $sourcefile )
	{
	    unlink($commandfile) || print "ERROR: could not remove $commandfile: $!\n";
	    $force_makefile = 1;
	}
    }
    
    # If the file .installtime exists, check to see if there are any files newer than that in the
    # 'command' filetree. If not, then none of the source files have changed and there is no need
    # to reinstall the command. But install anyway if --force was specified or if $force_makefile
    # is true.
    
    if ( -e "command/.installtime" && ! $options->{force} && ! $force_makefile )
    {
	# We wrap the call to 'find' in an eval, so if an error occurs we can gracefully
	# fail and install the command anyway.
	
	my $newerfiles;
	eval { $newerfiles = `find command -newer command/.installtime -print` };
	unless ( $newerfiles || $@ )
	{
	    print "\n - COMMAND [OK] None of the source files has changed\n";
	    return;
	}
    }
    
    # If this was called from 'update codebase' and the 'all' option was not specified, then ask
    # whether to reinstall the command.
    
    if ( $options->{update} && $options->{update} eq 'codebase' && ! $options->{all} )
    {
	my $answer = AskQuestion(" > COMMAND [OUT OF DATE] source files have changed. " .
				 "Reinstall the command? (y/n/q)", { yesnoquit => 1, default => 'yes' });

	exit if $answer eq 'quit';
	return unless $answer eq 'yes';
    }
    
    # If Makefile exists and if its last modification time is more recent than both Makefile.PL
    # and lib/PMCmd, then it does not need to be recompiled. But do so anyway if --force was
    # specified.
    
    unless ( -r "command/Makefile" &&
	     -M "command/Makefile" < -M "command/Makefile.PL" &&
	     -M "command/Makefile" < -M "command/lib/PMCmd" &&
	     -M "command/Makefile" < -M "command/script" &&
	     ! $CONFIG{install_bin_new} &&
	     ! $options->{force} &&
	     ! $force_makefile )
    {
	# If the user has specified a different install directory for binary files and scripts,
	# add that to the argument list.
	
	my $args = '';

	if ( $CONFIG{install_bin} || $CONFIG{install_bin_new} )
	{
	    my $install_bin = $CONFIG{install_bin_new} || $CONFIG{install_bin};
	    
	    $args = "INSTALLSITESCRIPT=$install_bin INSTALLSITEBIN=$install_bin";
	}
	
	# Generate the Makefile.
	
	print "> perl Makefile.PL $args\n";
	system("cd command; perl Makefile.PL $args");

	# Edit the Makefile to remove .ggpattern from the list of files to install.

	print q{> perl -pi -e "s/'?\S+[.]ggpattern'?//g" Makefile\n};
	system(q{cd command; perl -pi -e "s/'?\S+[.]ggpattern'?//g" Makefile});
    }
    
    # Make and install the command.
    
    print "\n# make\n";
    system("cd command; make") && exit;
    print "\n# make test\n";
    system("cd command; make test") && exit;
    print "\n# sudo make install\n";
    system("cd command; sudo make install") && exit;
    
    print "\n";
    
    # Check to make sure that the 'pbdb' and/or 'macrostrat' commands are runnable. If not, display an
    # error message and exit.
    
    my $pbdb_check = `which pbdb`;
    my $macro_check = `which macrostrat`;
    
    if ( ! $pbdb_check )
    {
	print "ERROR: the 'pbdb' command was not installed in any of the directories in your PATH.\n\n";
	print "You must re-run this install script as 'perl install.pl --install-bin=DIR', where DIR\n";
	print "is a directory in your path, i.e. /usr/bin or /usr/local/bin.\n\n";
	
	exit;
    }

    if ( ! $macro_check )
    {
	print "ERROR: the 'macrostrat' command was not installed in any of the directories in your PATH.\n\n";
	print "You must re-run this install script as 'perl install.pl --install-bin=DIR', where DIR\n";
	print "is a directory in your path, i.e. /usr/bin or /usr/local/bin.\n\n";
	
	exit;
    }
    
    # Create the .installtime file or set its modification time.
    
    system("touch command/.installtime");

    # If the 'restart' option was given, re-execute the command.

    if ( $options->{restart} )
    {
	print "\nRe-executing this command...\n\n";
	
	ExecCommand($0, @SAVE_ARGV);
    }
}


sub CreatePathFile {

    my $filename = 'command/lib/PMCmd/Path.pm';

    if ( -r $filename )
    {
	my $content = `cat $filename`;

	if ( $content =~ /$MAIN_PATH/ )
	{
	    return;
	}
    }
    
    open( my $path_file, '>', $filename ) ||
	die "ERROR: could not write $MAIN_PATH/$filename: $!\n";
    
    print $path_file <<EndContent;
# 
# This file stores the root path for the directory in which the project
# files manipulated by this command are kept. If the directory changes,
# cd to the new one and run 'perl install.pl command' to update it.

package PMCmd::Config;

our \$MAIN_PATH = "$MAIN_PATH";

EndContent
    
}


# ShowReposCmd ( options )
#
# Show all of the repositories known to this command, and the status of each one.

sub ShowReposCmd {

    my ($options) = @_;
    
    # If there is an argument, it should be a component name.

    my $filter = shift @ARGV;
    
    # Go through setup.yml and setup.override.yml looking for 'repository' entries.
    
    my @repo_list = ReadSetupFiles({ type => 'repository', filter => $filter });
    
    if ( ! $filter || $filter eq 'base' )
    {
	unshift @repo_list, { type => 'repository', path => $MAIN_PATH };
    }
    
    elsif ( $filter && @repo_list == 0 )
    {
	print "No repositories found for '$filter'\n";
	return ;
    }
    
    # Now go through the list and do a git status on each repository.

    my (@path, @status, @origin);

    my $red = "\033[0;31m";
    my $yellow = "\033[0;33m";
    my $green = "\033[0;32m";
    my $off = "\033[0m";
    
    if ( $options->{nocolor} )
    {
	$red = ''; $yellow = ''; $green = ''; $off = '';
    }
    
    foreach my $entry ( @repo_list )
    {
	my $path = $entry->{path};
	my $path = $path =~ qr{^/} ? $path : "$MAIN_PATH/$path";
	
	unless ( -d $path && -d "$path/.git" )
	{
	    push @path, "$red$path";
	    push @status, "repository not installed$off";
	    next;
	}
	
	my $status = CaptureCommand("cd $path; git status -b --porcelain");
	
	my @lines = split /[\n\r]+/, $status;
	
	if ( $lines[0] =~ / ^ [#][#] \s+ ([^.]+) .* (?: \[ ahead \s+ (\d+) \] )? /xs )
	{
	    my $branch = $1;
	    my $ahead = $2;
	    my $uncommitted = @lines > 1 && $lines[1] !~ /^[!?]/;
	    my $remote = '';
	    
	    my $color = $green;
	    $color = $yellow if $branch ne 'master';
	    $color = $red if $uncommitted || $ahead;
	    
	    my $message = "on branch '$branch'";
	    $message .= " uncommitted" if $uncommitted;
	    $message .= ", ahead of origin by $ahead commits" if $ahead;

	    if ( $options->{remote} )
	    {
		my ($origin) = CaptureCommand("cd $path; git remote get-url origin");
		chomp $origin;
		
		if ( $origin =~ qr{ ( [^/:]+ [/] [^/]+ [.] git ) $ }xs )
		{
		    $origin = $1;
		}
		
		push @origin, $origin;
		
		my $dryrun = CaptureCommand("cd $path; git fetch --dry-run origin $branch 2>&1");
		
		if ( $dryrun =~ qr{ ( [0-9a-f]+ [.][.] [0-9a-f]+ ) }xs )
		{
		    $message .= ", origin ahead";
		    $color = $red;
		}

		else
		{
		    $message .= ", up to date";
		}
	    }
	    
	    push @path, "$color$path";
	    push @status, "$message$off";
	}

	else
	{
	    push @path, "$red$path";
	    my $message = $lines[0] ? ": $lines[0]" : "";
	    push @status, "Error running 'git status'$message$off";
	    next;
	}
    }

    if ( $options->{remote} )
    {
	PrintOutputList($options, ['Repository path', 'Origin', 'Status'], \@path, \@origin, \@status);
    }

    else
    {
	PrintOutputList($options, ['Repository path', 'Status'], \@path, \@status);
    }
}


# ReadSetupFiles ( options )
#
# Read the master setup file and the local setup file. Any entries in the latter override entries
# with the same path in the former. Return a list of entry records.

my (%valid_type) = (repository => 1, dir => 1, symlink => 1, skip => 1);

sub ReadSetupFiles {
    
    my ($options) = @_;
    
    # Read setup information in YAML format from the master setup file. Index the list by path, so
    # that we can handle overrides.
    
    die "ERROR: 'master_setup' is not defined\n" unless $CONFIG{master_setup};
    
    unless ( -r $CONFIG{master_setup} )
    {
	die "ERROR: could not read $CONFIG{master_setup}: $!\n";
    }
    
    my $main_root = ReadConfigFile($CONFIG{master_setup});
    
    die "ERROR: the file $CONFIG{master_setup} must contain the key 'setup' with a list of actions\n"
	unless $main_root && $main_root->{setup} && ref $main_root->{setup} eq 'ARRAY';
    
    my @setup_list;
    my %setup_path;
    
    foreach my $index ( 1..@{$main_root->{setup}} )
    {
	my $entry = $main_root->{setup}[$index-1];
	
	# Skip any entries that aren't hash refs containing a 'path' attribute.
	
	unless ( ref $entry eq 'HASH' && $entry->{path} )
	{
	    print "WARNING: skipped entry $index from $CONFIG{master_setup} because it has no 'path' attribute\n"
		if $options->{verbose};
	    next;
	}

	unless ( $entry->{type} && $valid_type{$entry->{type}} )
	{
	    print "WARNING: skipped entry $index from $CONFIG{master_setup} because it does not specify " .
		"a valid type\n" if $options->{verbose};
	    next;
	}
	
	my $path = $entry->{path};
	
	# If we were given a type filter or a component filter, skip any entries that don't match.
	
	next if $options->{type} && $entry->{type} ne $options->{type};
	next if $options->{filter} && $entry->{component} ne $options->{filter};
	
	# If we encounter a duplicate 'path' entry, warn the user and mark the previous record as
	# overridden.
	
	if ( $setup_path{$path} )
	{
	    $setup_path{$path}{overridden} = 1;
	    print "WARNING: entry $index from $CONFIG{master_setup} overrides previous entry for '$path'\n"
		if $options->{verbose};
	}
	
	# Add this entry to the setup list.
	
	$entry->{source} = $CONFIG{master_setup};
	$setup_path{$path} = $entry;
	push @setup_list, $entry;
    }
    
    # Now read the local setup file, if one exists.
    
    # my $LOCAL_SETUP = $CONFIG{local_setup} || 'setup.override.yml';
    
    if ( $options->{verbose} && ! -r $LOCAL_SETUP )
    {
	print "WARNING: could not read $LOCAL_SETUP: $!\n";
    }
    
    my $local_root = ReadConfigFile($LOCAL_SETUP, { empty_ok => 1, absent_ok => 1 });
    
    if ( $local_root->{setup} && ref $local_root->{setup} eq 'ARRAY' )
    {
	foreach my $index ( 1..@{$local_root->{setup}} )
	{
	    my $entry = $local_root->{setup}[$index-1];
	    
	    # Skip any entries that aren't hash refs containing a 'path' attribute and a 'type'
	    # attribute.
	    
	    unless ( ref $entry eq 'HASH' && $entry->{path} )
	    {
		print "WARNING: skipped entry $index from $LOCAL_SETUP because " .
		    "it has no 'path' attribute\n" if $options->{verbose};
		next;
	    }
	    
	    unless ( $entry->{type} && $valid_type{$entry->{type}} )
	    {
		print "WARNING: skipped entry $index from $LOCAL_SETUP because it does not specify " .
		    "a valid type\n" if $options->{verbose};
		next;
	    }
	    
	    my $path = $entry->{path};
	    
	    # If we were given a type filter or a component filter, skip any entries that don't match.
	    
	    next if $options->{type} && $entry->{type} ne $options->{type};
	    next if $options->{filter} && $entry->{component} ne $options->{filter};
	    
	    # If we encounter a duplicate 'path' entry, warn the user and mark the previous record as
	    # overridden.
	    
	    if ( $setup_path{$path} )
	    {
		$setup_path{$path}{overridden} = 1;
		print "WARNING: entry $index from $LOCAL_SETUP overrides previous entry for '$path'\n"
		    if $options->{verbose} && $setup_path{$path}{source} eq $LOCAL_SETUP;
	    }
	    
	    # Add this entry to the setup list.
	    
	    $entry->{source} = $LOCAL_SETUP;
	    $setup_path{$path} = $entry;
	    push @setup_list, $entry;
	}
    }
    
    return grep { ! $_->{overridden} } @setup_list;
}


# Step 4 [config] - generate or update the main configuration files and the configuration files
# for the various services.

sub ConfigStep {

    my ($options) = @_;
    
    # Check for options after the step name
    
    my ($opt_reset, $opt_rebuild, $opt_merge);
    
    GetOptions('rebuild' => \$opt_rebuild,
	       'reset' => \$opt_reset,
	       'merge' => \$opt_merge);
    
    $options->{rebuild} = 1 if $opt_reset;
    $options->{merge} = 1 if $opt_merge;
    $options->{reset} = 1 if $opt_reset;
    
    # If this subroutine is run as the execution of either 'pbdb update config file', or
    # 'macrostrat update config file', select specific files according to the command-line
    # arguments and then update them to match the current values stored in the main configuration
    # file.
    
    if ( $options->{update} && $ARGV[0] eq 'file' )
    {
	die "The --reset option is not available with the 'file' argument. Use --rebuild instead.\n"
	    if $options->{reset};
	
	# Remove the argument 'file', and then look for one or more additional arguments
	# designating the file(s) to update. For each nonempty argument, search through the set of known
	# configuration files and ask the user whether to update any that match.
	
	shift @ARGV;
	
	unless ( @ARGV )
	{
	    print "\nYou must specify one or more files to update. Any arguments you provide\n";
	    print "will be matched against the names of the various configuration files for\n";
	    print "installed project components.\n\n";
	    
	    exit 2;
	}
	
	my (@update_list, %file_matched);

	while ( @ARGV )
	{
	    my $arg = shift @ARGV;
	    next unless $arg;

	    # Check for options

	    if ( $arg =~ /^-/ )
	    {
		if ( $arg eq '--rebuild' )
		{
		    $options->{rebuild} = 1;
		}

		elsif ( $arg eq '--merge' )
		{
		    $options->{merge} = 1;
		}
		
		else
		{
		    die "ERROR: unknown option '$arg'\n";
		}
		
		next;
	    }
	    
	    # Otherwise, create a regex for searching.
	    
	    $arg =~ s/[*]/.*/g;
	    my $matcher = qr{$arg};
	    
	    # Check each file for a match against its designation, its component, and its
	    # filename. If a file already matched a previous argument, don't consider it
	    # again.
	    
	    foreach my $entry ( @MAIN_CONF, @COMPONENT_CONF )
	    {
		my $component = $entry->{component};
		my $filename = $entry->{filename};
		
		next if $file_matched{$filename};
		next unless $CONFIG{"include_$component"} eq 'yes';
		
		if ( $component eq $arg || $filename =~ $matcher )
		{
		    $file_matched{$filename} = 1;
		    
		    my $answer = AskQuestion("Update file $filename ($component)?",
					 { yesno => 1, default => "yes" });
		    
		    if ( $answer eq 'yes' )
		    {
			push @update_list, $entry;
		    }
		}
	    }
	}
	
	# If one or more files were selected, rewrite just those files. Use the %CONFIG hash, so
	# that the current value of each relevant setting is substituted into each file.
	
	if ( @update_list )
	{
	    RewriteConfigFiles(\@update_list, \%CONFIG, $options);
	}
	
	else
	{
	    print "No files matched the arguments given\n";
	}
	
	return;
    }
    
    # Otherwise, if this subroutine was run as the execution of 'pbdb update config' or
    # 'macrostrat update config', then check to see if the user specified either a project component
    # or else the 'general' configuration group. The argument 'pbdb' is accepted as an alias for
    # 'paleobiodb' and 'macro' as an alias for 'macrostrat'. If this subroutine was run from
    # install.pl, run through all of the configuration groups.
    
    my $select_group = 'all';
    
    if ( $options->{update} )
    {
	$select_group = shift @ARGV if $ARGV[0];
	
	$select_group =~ s/^pbdb$/paleobiodb/;
	$select_group =~ s/^macro$/macrostrat/;
	
	unless ( $select_group eq 'general' || $select_group eq 'all' || $COMPONENT{$select_group} )
	{
	    if ( exists $CONFIG{"include_$select_group"} )
	    {
		print "Project component '$select_group' is not installed.\n";
		return;
	    }
	    
	    else
	    {
		print "Configuration group '$select_group' was not found.\n";
		return;
	    }
	}

	# Check to see if any options were specified later.

	if ( @ARGV )
	{
	    if ( $ARGV[0] eq '--rebuild' )
	    {
		$options->{rebuild} = 1;
	    }

	    elsif ( $ARGV[0] eq '--merge' )
	    {
		$options->{merge} = 1;
	    }

	    elsif ( $ARGV[0] =~ /^-/ )
	    {
		die "ERROR: unknown option '$ARGV[0]'\n";
	    }

	    else
	    {
		die "ERROR: extra argument '$ARGV[0]' not allowed\n";
	    }
	}
    }
    
    # If the --reset option was specified, ask if that is what the user really wants to do. If
    # yes, reset %CONFIG to %DEFAULT and then run &ProjectStep.
    
    if ( $options->{reset} )
    {
	my $dothis = AskQuestion("Do you want to DISCARD all configuration settings and start again from defaults?",
			     { yesno => 1 });
	
	return unless $dothis eq 'yes';

	%CONFIG = %DEFAULT;
	
	&ProjectStep({ %$options, force => 1 });
    }
    
    # Now make sure that all of the configuration files are in place. If they don't already
    # exist, copy them from the corresponding template files. If a particular configuration group
    # was selected, only check that group's files.
    
    EnsureConfigFiles($options, $select_group);
    
    # If we are running from install.pl, print out a brief introduction.
    
    if ( $options->{install} )
    {
	print <<EndIntro;

This script will now ask you some questions about how you want this site configured.
If you make a mistake, quit this script and rerun with the argument 'config' to start
this step over. In most cases, you can just hit 'enter' on each question to accept the
defaults.

EndIntro
    }

    else
    {
	print "\n";
    }
    
    # If the --reset option was given, reset everything back to the defaults. Run the 
    
    # Determine which project components are installed.
    
    my $include_paleobiodb = $CONFIG{include_paleobiodb} eq 'yes' ? 1 : 0;
    my $include_macrostrat = $CONFIG{include_macrostrat} eq 'yes' ? 1 : 0;
    my $include_earthlife = $CONFIG{include_earthlife} eq 'yes' ? 1 : 0;
    my $include_rockd = $CONFIG{include_rockd} eq 'yes' ? 1 : 0;
    my $include_mibasin = $CONFIG{include_mibasin} eq 'yes' ? 1 : 0;
    
    # Then check the local hostname. If the output of 'hostname -f' gives a name whose IP address
    # is not in the private network range, we can use that as the domain for project components
    # installed here. Otherwise, we will use names such as 'paleobiodb.local', 'macrostrat.local',
    # etc.
    
    my $dflt_hostname = CaptureCommand("hostname -f");
    chomp $dflt_hostname;
    
    my $dflt_addr = CaptureCommand("host $dflt_hostname");
    
    my $known_hostname;
    
    if ( $dflt_hostname && $dflt_hostname =~ /[.]/ && $dflt_hostname !~ /[.]lan$/ &&
	 $dflt_addr && $dflt_addr !~ /^10[.]|196[.]168/ )
    {
	$known_hostname = $dflt_hostname;
    }
    
    # Grab the contents of /etc/hosts.
    
    my $local_hostnames = CaptureCommand('cat /etc/hosts');
    
    # Go through the selected configuration group(s) and collect all updates in %updates.
    
    my %updates;
    
    # If paleobiodb is included and we are configuring it, do so now.
    
    if ( $include_paleobiodb && ( $select_group eq 'all' || $select_group eq 'paleobiodb' ) )
    {
	print "Paleobiology Database configuration:\n";
	print "------------------------------------\n";
	
	# The most important question is whether this installation is going to be one of the
	# official webservers or just a locally available installation.
	
	my $local_domain = $known_hostname || 'paleobiodb.local';
	
	my $site_choice = ChooseSite('paleobiodb', $COMPONENT{paleobiodb},
				     $CONFIG{site_paleobiodb}, $local_domain, $local_hostnames);
	
	$updates{site_paleobiodb} = $site_choice;
	
	$updates{pbdb_domain} = $COMPONENT{paleobiodb}{website}{$site_choice} || $local_domain;
	
	# Once this choice is made, the next choice is how many api server processes and classic
	# server processes to maintain. The default for this question depends on which option was
	# chosen above, and also on whether specific defaults are stored in the configuration
	# file. We have hardcoded failsafe defaults just in case the configuration information cannot be
	# read properly.
	
	$site_choice ||= 'local';
	
	my $pbapi_default = $CONFIG{"workers_paleobiodb_pbapi_$site_choice"} ||
	    $COMPONENT{paleobiodb}{workers}{$site_choice}{pbapi} ||
	    $COMPONENT{paleobiodb}{workers}{default}{pbapi};
	
	$pbapi_default = '3' unless $pbapi_default && $pbapi_default =~ /^\d+$/;
	
	my $classic_default = $CONFIG{"workers_paleobiodb_classic_$site_choice"} ||
	    $COMPONENT{paleobiodb}{workers}{$site_choice}{classic} ||
	    $COMPONENT{paleobiodb}{workers}{default}{classic};
	
	$classic_default = '3' unless $classic_default && $classic_default =~ /^\d+$/;
	
	my $nginx_default = $CONFIG{"workers_paleobiodb_nginx_$site_choice"} ||
	    $COMPONENT{paleobiodb}{workers}{$site_choice}{nginx} ||
	    $COMPONENT{paleobiodb}{workers}{default}{nginx};
	
	$nginx_default = '3' unless $nginx_default && $nginx_default =~ /^\d+$/;
	
	$updates{pbapi_workers} = AskQuestion("How many api worker processes should be run on this server?",
					  { default => $pbapi_default, posint => 1 });
	
	$updates{"workers_paleobiodb_pbapi_$site_choice"} = $updates{pbapi_workers};
	
	$updates{classic_workers} = AskQuestion("How many classic worker processes should be run on this server?",
					    { default => $classic_default, posint => 1 });
	
	$updates{"workers_paleobiodb_classic_$site_choice"} = $updates{classic_workers};
	
	$updates{nginx_workers} = AskQuestion("The nginx worker processes are shared between all installed project components.\nHow many nginx worker processes should be run on this server?",
					  { default => $nginx_default, posint => 1 });
	
	$updates{"workers_paleobiodb_nginx_$site_choice"} = $updates{nginx_workers};
	
	# If this is one of the official pbdb sites, it will need to be able to send out e-mail to
	# users. So we must configure the smtp hostname and port if so.

	if ( $site_choice && $site_choice ne 'local' )
	{
	    $updates{smtp_host} = AskQuestion("SMTP hostname for mail relay:",
					  { default => $CONFIG{smtp_host} });

	    $updates{smtp_port} = AskQuestion("SMTP port for mail relay:",
					  { default => $CONFIG{smtp_port} });
	}
	
	# The next series of questions set defaults for fetching paleobiology database content
	# from a remote server. In almost all cases, the user can just accept the default
	# values.
	
	$updates{pbdb_master_login} = AskQuestion("If you have a login on a server with a copy of the paleobiology database,\nenter your username or 'none':",
						  { default => $CONFIG{pbdb_master_login} } );
	
	$updates{pbdb_master_login} = '' if $updates{pbdb_master_login} eq 'none' || $updates{pbdb_master_login} =~ /^\s+$/;
	
	my $select = $updates{pbdb_master_login} ? 'master' : 'public';
	
	my $default_host = $CONFIG{"pbdb_${select}_host"};
	
	my $choose_host = AskQuestion("Remote host from which to pull paleobiology database contents:",
				  { default => $default_host });

	if ( $choose_host ne $default_host )
	{
	    $updates{"pbdb_${select}_host"} = $choose_host;
	}
	
	my $select_dirs = AskQuestion("Use the default directories for fetching backup content from $choose_host?",
				      { yesno => 1, default => 'yes' });
	
	if ( $select_dirs eq 'no' )
	{
	    $updates{"pbdb_${select}_backup_dir"} =
		AskQuestion("Directory on $choose_host where backups are stored:",
			    { default => $CONFIG{"pbdb_${select}_backup_dir"} });
	    
	    $updates{"pbdb_${select}_image_dir"} =
		AskQuestion("Directory on $choose_host where images are stored:",
			    { default => $CONFIG{"pbdb_${select}_image_dir"} });
	    
	    $updates{"pbdb_${select}_archive_dir"} =
		AskQuestion("Directory on $choose_host where archives are stored:",
			    { default => $CONFIG{"pbdb_${select}_archive_dir"} });
	    
	    $updates{"pbdb_${select}_datalog_dir"} =
		AskQuestion("Directory on $choose_host where datalogs are stored:",
			    { default => $CONFIG{"pbdb_${select}_datalog_dir"} });
	}
	
	# For the initial installation only, we ask the user to choose a database username and
	# password for the paleobiodb API or else accept the default choices. These can later
	# be updated using the commands 'pbdb update api username' and 'pbdb update api password'.
	
	unless ( $options->{update} || $options->{reset} )
	{
	    print "\nChoose a database username and password for the API:\n";
	    
	    $updates{pbdb_username} = AskQuestion("Username:",
						  { default => $CONFIG{pbdb_username} });
	    
	    while ( 1 )
	    {
		$updates{pbdb_password} = AskQuestion("Password:",
						      { default => $CONFIG{pbdb_password} });
		
		last if $updates{pbdb_password} !~ /['"]/;
		
		print "Please enter a password that does not contain any quotation marks.\n";
	    }
	}

	print "\n";
    }
    
    # If earthlife is included and we are configuring it, do so now.
    
    if ( $include_earthlife && ( $select_group eq 'all' || $select_group eq 'earthlife' ) )
    {
	print "Earthlife configuration:\n";
	print "------------------------\n";
	
	# The main question in this section is whether this installation is going to be one of the
	# official webservers or just a locally available installation. If this is one of the
	# official paleobiodb.org sites (but not training) then offer that as the default for earthlife
	# too.
	
	my $local_domain = $known_hostname || 'earthlife.local';
	my $site_default = $CONFIG{site_earthlife} || $updates{site_paleobiodb} // $CONFIG{site_paleobiodb};
	
	$site_default = '' if $site_default eq 'training';
	
	my $site_choice = ChooseSite('earthlife', $COMPONENT{earthlife}, $site_default,
				     $local_domain, $local_hostnames);
	
	$updates{site_earthlife} = $site_choice;

	# Once this choice is made, ask how many server processes to run.
	
	$site_choice ||= 'local';
	
	my $earthlife_default = $CONFIG{"workers_earthlife_$site_choice"} ||
	    $COMPONENT{earthlife}{workers}{$site_choice}{earthlife} ||
	    $COMPONENT{earthlife}{workers}{default}{earthlife};
	
	$earthlife_default = '3' unless $earthlife_default && $earthlife_default =~ /^\d+$/;
	
	$updates{earthlife_workers} = AskQuestion("How many earthlife api worker processes should be run on this server?",
					      { default => $earthlife_default, posint => 1 });
	
	$updates{"workers_earthlife_$site_choice"} = $updates{earthlife_workers};
    }
    
    # If macrostrat is included and we are configuring it, do so now.
    
    if ( $include_macrostrat && ( $select_group eq 'macrostrat' || $select_group eq 'all' ) )
    {
	print "Macrostrat configuration:\n";
	print "-------------------------\n";
	
	# The most important question is whether this installation is going to be one of the
	# official webservers or just a locally available installation.
	
	my $local_domain = $known_hostname || 'macrostrat.local';
	
	my $site_choice = ChooseSite('macrostrat', $COMPONENT{macrostrat},
				     $CONFIG{site_macrostrat}, $local_domain, $local_hostnames);
	
	$updates{site_macrostrat} = $site_choice;
	
	$updates{macro_domain} = $COMPONENT{mactrostrat}{website}{$site_choice} || $local_domain;
	
	# Once this choice is made, ask how many nginx processes to run.
	
	$site_choice ||= 'local';
	
	my $macrostrat_default = $CONFIG{"workers_macrostrat_nginx_$site_choice"} ||
	    $COMPONENT{macrostrat}{workers}{$site_choice}{nginx} ||
	    $COMPONENT{macrostrat}{workers}{default}{nginx};
	
	$macrostrat_default = '3' unless $macrostrat_default && $macrostrat_default =~ /^\d+$/;
	
	# If there is already a larger number of processes chosen for the paleobiodb, override the
	# default and use that one.
	
	my $pbdb_choice = $updates{site_paleobiodb} || $CONFIG{site_paleobiodb};
	
	my $previous_default = $pbdb_choice && $CONFIG{"workers_paleobiodb_nginx_$pbdb_choice"};
	
	if ( $previous_default && $previous_default > $macrostrat_default )
	{
	    print "\nThe number of nginx worker processes you chose for the pbdb is $previous_default.\n";
	    print "You should keep this number unless macrostrat needs more, because the\n";
	    print "pool of nginx worker processes is shared among all installed components.\n";
	    
	    $macrostrat_default = $previous_default;
	}
	
	my $nginx_workers = AskQuestion("How many nginx worker processes should be run on this server?",
				    { default => $macrostrat_default, posint => 1 });
	
	# If the number of nginx workers was already set above, don't lower it. But record the
	# actual answer to this question in the configuration file for use as a default later.
	
	unless ( $updates{nginx_workers} && $nginx_workers <= $updates{nginx_workers} )
	{
	    $updates{nginx_workers} = $nginx_workers;
	}
	
	$updates{"workers_macrostrat_nginx_$site_choice"} = $nginx_workers;
	
	# We then need a default hostname for fetching macrostrat database content.
	
	$updates{macro_master_login} = AskQuestion("If you have a login on the macrostrat master server, enter your username or 'none':",
						  { default => $CONFIG{macro_master_login} } );
	
	$updates{macro_master_login} = '' if $updates{macro_master_login} eq 'none' || $updates{macro_master_login} =~ /^\s+$/;
	
	my $select = $updates{macro_master_login} ? 'master' : 'public';
	
	my $default_host = $CONFIG{"macro_${select}_host"};
	
	my $choose_host = AskQuestion("Remote host from which to pull database contents:",
				  { default => $default_host });

	if ( $choose_host ne $default_host )
	{
	    $updates{"macro_${select}_host"} = $choose_host;
	}
	
	# For the initial installation only, we ask the user to choose a database username and
	# password for the macrostrat API or else accept the default choices. These can later
	# be updated using the commands 'macrostrat update api username' and
	# 'macrostrat update api password'.
	
	unless ( $options->{update} || $options->{reset} )
	{
	    print "\nChoose a database username and password for the API:\n";
	    
	    $updates{macro_username} = AskQuestion("Username:",
						  { default => $CONFIG{macro_username} });
	    
	    while ( 1 )
	    {
		$updates{macro_password} = AskQuestion("Pasword:",
						      { default => $CONFIG{macro_password} });
		
		last if $updates{macro_password} !~ /['"]/;
		
		print "Please enter a password that does not contain any quotation marks.\n";
	    }
	}

	# Ask for the mapzen key.
	
	$updates{macro_mapzen_key} = AskQuestion("Enter the mapzen key for the API:",
					     { default => $CONFIG{macro_mapzen_key} } );
	
	# If any of the macrostrat v2 api settings has changed, generate a new cache refresh key.

	if ( $updates{macro_username} || $updates{macro_password} || $updates{macro_mapzen_key} )
	{
	    my $new_key = `uuidgen`;
	    chomp $new_key;
	    
	    $updates{macro_refresh_key} = $new_key;
	}
	
	# Ask for the secret key for the tileserver.
	
	$updates{macro_tileserver_secret} = AskQuestion("Enter the secret key for the tileserver:",
						    { default => $CONFIG{macro_tileserver_secret} } );
	
	print "\n";
    }
    
    # If rockd is included and we are configuring it, do so now.
    
    if ( $include_rockd && ( $select_group eq 'all' || $select_group eq 'rockd' ) )
    {
	print "Rockd configuration:\n";
	print "--------------------\n";
	
	# The only question in this section is whether this installation is going to be one of the
	# official webservers or just a locally available installation.
	
	my $local_domain = $known_hostname || 'rockd.local';
	my $site_default = $CONFIG{site_rockd} || $updates{site_macrostrat} // $CONFIG{site_macrostrat};
	
	$site_default = '' if $site_default eq 'training';
	
	$updates{site_rockd} = ChooseSite('rockd', $COMPONENT{rockd}, $site_default,
					  $local_domain, $local_hostnames);
	
	# The rockd component does not require any configuration of worker processes. The main
	# path does need to be set, however.
	
	$updates{rockd_mainpath} = "$MAIN_PATH/frontend/rkapi/rockd-ionic";
	
	# Ask for the token secret and the API key for sending e-mail.

	$updates{rockd_tokensecret} = AskQuestion("Enter the rockd token secret:",
					      { default => $CONFIG{rockd_tokensecret} });

	
	$updates{rockd_mail_key} = AskQuestion("Enter the API key for rockd to use when sending e-mail:",
					   { default => $CONFIG{rockd_mail_key} } );
	
	# For the initial installation only, we ask the user to choose a database username and
	# password for the rockd API or else accept the default choices. These can later
	# be updated using the commands 'macrostrat update rockd username' and
	# 'macrostrat update rockd password'.
	
	unless ( $options->{update} || $options->{reset} )
	{
	    print "\nChoose a database username and password for the API:\n";
	    
	    $updates{rockd_username} = AskQuestion("Username:",
						  { default => $CONFIG{rockd_username} });
	    
	    while ( 1 )
	    {
		$updates{rockd_password} = AskQuestion("Pasword:",
						      { default => $CONFIG{rockd_password} });
		
		last if $updates{rockd_password} !~ /['"]/;
		
		print "Please enter a password that does not contain any quotation marks.\n";
	    }
	}
    }
    
    # If mibasin is included and we are configuring it, do so now.
    
    if ( $include_mibasin && ( $select_group eq 'all' || $select_group eq 'mibasin' ) )
    {
	print "Michigan Basin Fossils configuration:\n";
	print "-------------------------------------\n";
	
	# The only question in this section is whether this installation is going to be one of the
	# official webservers or just a locally available installation.
	
	my $local_domain = $known_hostname || 'mibasin.local';
	my $site_default = $CONFIG{site_mibasin} || $updates{site_macrostrat} // $CONFIG{site_macrostrat};
	
	$site_default = '' if $site_default eq 'training';
	
	my $site_choice = ChooseSite('mibasin', $COMPONENT{mibasin}, $site_default,
				     $local_domain, $local_hostnames);
	
	$updates{site_mibasin} = $site_choice;
	
	# The mibasin component does not require any configuration of worker processes.
	
	# For the initial installation only, we ask the user to choose a database username and
	# password for the macrostrat API or else accept the default choices. These can later
	# be updated using the commands 'macrostrat update api username' and
	# 'macrostrat update api password'.
	
	unless ( $options->{update} || $options->{reset} )
	{
	    print "\nChoose a database username and password for the API:\n";
	    
	    $updates{mibas_username} = AskQuestion("Username:",
						  { default => $CONFIG{mibas_username} });
	    
	    while ( 1 )
	    {
		$updates{mibas_password} = AskQuestion("Pasword:",
						      { default => $CONFIG{mibas_password} });
		
		last if $updates{mibas_password} !~ /['"]/;
		
		print "Please enter a password that does not contain any quotation marks.\n";
	    }
	}
    }
    
    # Now we move on to general configuration settings.
    
    if ( $select_group eq 'all' || $select_group eq 'general' )
    {
	print "General configuration:\n";
	print "----------------------\n";
	
	# If the letsencrypt package is installed on this system, locate it.
	
	if ( -e "/etc/letsencrypt" )
	{
	    $updates{letsencrypt_path} = "/etc/letsencrypt";
	    print "\nFound Let's Encrypt directory at /etc/letsencrypt\n";
	}
	
	elsif ( -e "/opt/local/etc/letsencrypt" )
	{
	    $updates{letsencrypt_path} = "/opt/local/etc/letsencrypt";
	    print "\nFound Let's Encrypt directory at /opt/local/etc/letsencrypt\n";
	}
	
	elsif ( $CONFIG{letsencrypt_path} )
	{
	    $updates{letsencrypt_path} = '';
	}

	# Check for the gunzip command. If we don't find it, ask the user which command to use.
	
	my $unzip_cmd = CaptureCommand("which gunzip");

	if ( $unzip_cmd =~ /\bgunzip$/ )
	{
	    $updates{unzip_cmd} = 'gunzip -c';
	}
	
	else
	{
	    print "\nThe gunzip command was not found. Which command should be used to uncompress .gz files?\n";
	    $unzip_cmd = AskQuestion("Enter the full pathname of the command, and include any necessary\n" .
				      "options for decompressing to standard output:",
				      { optional => 1 });
	    
	    $updates{unzip_cmd} = $unzip_cmd if $unzip_cmd;
	}
	
	# Choose the timezone setting for containers. In almost all cases, this will be the
	# timezone that is set for the host. Unfortunately, the method of determining this varies
	# from operating system to operating system.
	
	my $local_timezone;
	
	my $uname = CaptureCommand("uname");
	
	if ( $uname =~ /Darwin/ )
	{
	    $local_timezone = CaptureCommand("sudo systemsetup -gettimezone");
	    $local_timezone =~ s/^.*:\s+//;
	    chomp $local_timezone;
	}
	
	else
	{
	    $local_timezone = CaptureCommand("cat /etc/timezone");
	    chomp $local_timezone;
	}
	
	$updates{local_timezone} = AskQuestion("Local timezone:", { default => $CONFIG{local_timezone} || $local_timezone });
	
	# Now set a directory to which local backup files should be written.
	
	$updates{backup_dir} = AskQuestion("Local directory for backup files:",
				           { default => $CONFIG{backup_dir} });
	
	# If the user selected a directory other than the default for installing executables,
	# write that to the proper configuration setting name now. The user has already made that
	# choice by specifying an option to install.pl, so there is no need to ask anything now.
	
	$updates{install_bin} = $CONFIG{install_bin_new} if $CONFIG{install_bin_new} ne $CONFIG{install_bin};
	
	# For the initial installation only, we ask the user to choose a database username and
	# password for executive access or else accept the default choices. These can later
	# be updated using the commands 'macrostrat update exec username' and
	# 'macrostrat update exec password'.
	
	unless ( $options->{update} || $options->{reset} )
	{
	    print "\nChoose a database username and password for executive functions (i.e. altering tables):\n";
	    
	    $updates{exec_username} = AskQuestion("Username:", { default => $CONFIG{exec_username} });
	    
	    while ( 1 )
	    {
		$updates{exec_password} = AskQuestion("Password:", { default => $CONFIG{exec_password} });
		
		last if $updates{exec_password} !~ /['"]/;    #'
		
		print "Please enter a password that does not contain any quotation marks.\n";
	    }
	    
	    print <<EndNote;

Note: this username and password will be able to see all databases and has permission to
add and drop tables and carry out other privileged operations. However, you will need to
log in as root in order to create accounts or change passwords.

EndNote
	}

	print "\n";
    }
    
    # Now write out all changes that have been made.
    
    print "Results\n";
    print "-------\n";

    # If the base for the main configuration file is newer than the file itself (which will happen
    # if the base repository has been pulled recently) then regenerate the main configuration file
    # from the new base and the newly entered set of configuration settings and updates. Otherwise,
    # rewrite the existing configuration file with the new updates.
    
    RewriteLocalConfig(\%updates, $options);
    
    print "\n";
    
    # Then rewrite all of the other configuration files, according to the options chosen above. If
    # this subroutine is being run as an update command, this may cause some services to be rebuilt.
    
    RewriteConfigFiles('all', \%updates, $options);
}


# ChooseSite ( )
#
#

sub ChooseSite {

    my ($component_name, $component_data, $default, $local_domain, $local_hostnames) = @_;
    
    my @choice_list = qw(main dev);
    
    foreach my $other ( sort keys %{$component_data->{website}} )
    {
	push @choice_list, $other if $other ne 'main' && $other ne 'dev';
    }
    
    my @ask_list = map { $_, $component_data->{website}{$_} } @choice_list;
    push @ask_list, '-', '-----------------', '', $local_domain;
    
    my $label = $component_data->{label} || $component_name;
    
    my $site_choice = AskChoice("Will this installation be an official $label server, or a local site?",
			        { default => $default, number_choices => 1, return_choice => 1 },
				@ask_list);
    
    if ( $site_choice eq '' && $local_domain =~ /[.]local$/ )
    {
	unless ( $local_hostnames && $local_hostnames =~ /$local_domain/ )
	{
	    print "\nNOTE: In order to use '$local_domain', you must map that name to 127.0.0.1 in /etc/hosts.\n";
	}
    }

    print "\n";

    return $site_choice;
}


# EnsureConfigFiles ( )
# 
# Make sure that all of the configuration files listed in %CONF_FILE exist, for each project
# component.

sub EnsureConfigFiles {
    
    my ($options, $check_component) = @_;
    
    my $errors;
    
    # Go through @MAIN_CONF and @COMPONENT_CONF and check to make sure all of the listed files
    # exist. For any that do not, copy from the corresponding base file. If a specific project
    # component is selected, only check files from that project.
    
    foreach my $entry ( @MAIN_CONF, @COMPONENT_CONF )
    {
	my $component = $entry->{component};
	
	if ( $check_component eq 'all' || $component eq $check_component )
	{
	    if ( $component eq 'main' ||
		 $COMPONENT{$component}{path} && -d $COMPONENT{$component}{path} )
	    {
		PrintDebug("Checking that file $entry->{filename} exists") if $DEBUG;
		EnsureFile($entry->{filename}, $entry->{basename}, { optional => 1 }) || $errors++;
	    }
	}
    }
    
    if ( $errors )
    {
	print "\nSome files could not be created. You will have to fix the problem,\n";
	print "and re-run the command '$COMMAND update config'.\n";
    }
}


# EnsureFile ( target, source, options )
# 
# If the file named by $target does not exist, create it by copying the file named by $source. If
# the file does not have the proper filemode, attempt to chmod it. If the file cannot be copied,
# or if it exists but is not readable or not writable, then throw an exception unless $optional is
# true. In that case, just return false.

sub EnsureFile {

    my ($target, $source, $options) = @_;
    
    $options ||= { };
    
    # First determine the proper filemode. If the 'executable' option is given, set the executable
    # bit whenever either or both of read or write is set.
    
    my $filemode = $CONFIG{file_permissions} || "f0644";
    $filemode =~ tr/a-z//d;
    
    if ( $options->{executable} )
    {
	$filemode =~ tr/642/751/;
    }
    
    my $nummode = oct($filemode);
    
    # If the file does not exist, create it and make sure it has the proper filemode. If an error
    # occurs, store the message in the variable $error so that we can decide below whether to
    # throw it or print it as a warning.
    
    my $condition;
    
    if ( ! -e $target )
    {
	print STDOUT "Copying $source to $target\n";
	
	if ( copy($source, $target) )
	{
	    my $perms = (stat($target))[2] & 07777;
	    
	    if ( ! $perms )
	    {
		$condition = "could not stat $target: $!";
	    }
	    
	    elsif ( $perms && $perms != $nummode )
	    {
		chmod($nummode, $target) || ($condition = "could not chmod $target: $!");
	    }
	}
	
	else
	{
	    $condition = "could not copy $source to $target: $!";
	}
    }
    
    # If the file exists but is not readable and writable, report that. This almost certainly
    # means that the file is owned by somebody else and the file permissions are not set
    # correctly.
    
    elsif ( ! -r $target )
    {
	$condition = "$target exists but is not readable";
    }

    elsif ( ! -w $target )
    {
	$condition = "$target exists but is not writeable";
    }

    # If an error occurred, throw an exception unless the 'optional' option was specified. In that
    # case, we print a warning and return false.

    if ( $condition )
    {
	if ( $options->{optional} )
	{
	    print "WARNING: $condition\n";
	    return;
	}
	
	else
	{
	    die "ERROR: $condition\n";
	}
    }

    # Otherwise, the file is there and we can read and write it. Everything is fine, so return true.  
    # If $DEBUG is set, note that the file exists.
    
    else
    {
	print STDOUT "Found $target\n" if $DEBUG;
	return 1;
    }
}


my (%deprecated_key) = ( website_main => 1, webproto_hostname => 1, website_local => 1,
			 paleobiodb_site => 1, earthlife_site => 1, pbdb_site => 1 );

# RewriteLocalConfig ( updates, options )
# 
# Rewrite the local configuration file, applying the changes to configuration settings specified
# by $updates. The value of $updates must be a hashref whose keys are configuration setting names
# with the new values for those settings. No rewrite will be done unless at least one of those
# values differs from the current value in the %CONFIG hash. If the option --reset was specified,
# or if the base configuration file is newer than the local configuration file due to a repository
# update, then the file will be rewritten using the new base file as a template. Otherwise, it
# will be rewritten starting with the current file as a template. In either case, all of the
# settings in the current file will be written to the new file except for any that are deprecated
# or whose new value is the same as the default.

sub RewriteLocalConfig {
    
    my ($updates, $options) = @_;
    
    $options ||= { };
    
    # Decode the current configuration file contents into a hashref, and then apply the updates.
    # Update %CONFIG as well, so that the new values will be used during the rest of the current
    # execution. Set %updated for each value that is actually different than the current contents
    # of the configuration file.
    
    my $config_data = ReadConfigFile($LOCAL_CONFIG, { empty_ok => 1 });
    
    my %updated;
    
    foreach my $key ( keys %$updates )
    {
	# If the updated value for this setting is defined and the current configuration file
	# specifies either a different value for this setting or no value at all, then apply the
	# update.
	
	if ( defined $updates->{$key} )
	{
	    if ( ! defined $config_data->{$key} || $updates->{$key} ne $config_data->{$key} )
	    {
		$config_data->{$key} = $updates->{$key};
		$CONFIG{$key} = $updates->{$key};
		$updated{$key} = 1;
	    }
	}
	
	# If the new value is undefined but the old value was not, then this setting will revert
	# to its default value.
	
	elsif ( defined $config_data->{$key} )
	{
	    $config_data->{$key} = $DEFAULT{$key};
	    $CONFIG{$key} = $DEFAULT{$key};
	    $updated{$key} = 1;
	}
	
	# If this setting specifies the inclusion or uninclusion of a project, update the
	# %COMPONENT hash as well. The default value for all project components is 'no'.
	
	if ( $updated{$key} && $key =~ /^include_(\w+)/ )
	{
	    if ( $config_data->{$key} && $config_data->{$key} eq 'yes' )
	    {
		$COMPONENT{$1} ||= { };
	    }
	    
	    else
	    {
		delete $COMPONENT{$1};
	    }
	}
    }
    
    # Then check to see whether the configuration file or its base file is newer. If it is the
    # latter, print out an explanatory message and build the new contents using the base file as a
    # template. Also do this if the --reset option was given, regardless of which file is newer.
    
    my @config_lines;
    my $updated_settings;
    
    my $config_base = $CONFIG{main_config_base} || 'project/config-base.yml';
    
    if ( -M $config_base && -M $LOCAL_CONFIG && -M $config_base < -M $LOCAL_CONFIG || $options->{reset} )
    {
	print "\n";
	print "The file $config_base is newer than $LOCAL_CONFIG.\n" unless $options->{reset};
	print "Rebuilding $LOCAL_CONFIG from $config_base.\n\n";
	
	# Read the raw contents of the base file.
	
	open(my $icfg, "<", $config_base) || die "ERROR: could not read $config_base: $!\n";
	
	@config_lines = <$icfg>;
	
	close $icfg;
	
	# Go through the lines read from the base file, and whenever we find a line that matches a
	# setting that we have a value for, substitute that value in.
	
	foreach my $line ( @config_lines )
	{
	    if ( $line =~ qr{ ^ ( [#] \s )? (\w+) \s* [:] \s* (.*) $ }xs )
	    {
		my $comment = $1;
		my $key = $2;
		
		# If we have a value for the setting specified on this line, and the value is
		# different from the default, then substitute it. Here we are relying on the
		# behavior of foreach in Perl. Modifying $line also modifies the corresponding
		# element in @config_lines.
		
		if ( defined $config_data->{$key} && $config_data->{$key} ne $DEFAULT{$key} )
		{
		    # Use YAML::Tiny to encode the new setting, then remove any initial line(s)
		    # starting with ---. The regex \s ^ matches the newline at the end of these
		    # lines, which we want to remove along with the line contents.
		    
		    my $new_line = YAML::Tiny::Dump({ $key => $config_data->{$key} });
		    $new_line =~ s/ \A (?: -.* \s ^ )+ //mx;
		    
		    $line = $new_line;
		    $updated_settings++;
		}
		
		# The setting lines in the base configuration file are supposed to all be
		# commented out. But in case this changes in the future, any uncommented line
		# that matches a setting whose updated value is equal to the default should be
		# written in a commented-out state.
		
		elsif ( ! $comment )
		{
		    $line = "# " . $line;
		    $updated_settings++;
		}
		
		# In either case, delete this setting so it will not be written out at the end.
		
		delete $config_data->{$key};
	    }
	}
    }
    
    # Otherwise, if no updates are recorded then just return true. That indicates that the current
    # contents of the configuration file are consistent with the updated values.
    
    elsif ( ! %updated )
    {
	print "No changes were made to $LOCAL_CONFIG\n";
	return 1;
    }
    
    # If we need to make some updates, use the existing contents of the configuration file as the
    # template. Read it in as a sequence of raw lines.
    
    else
    {
	open(my $icfg, "<", $LOCAL_CONFIG) || die "ERROR: could not read $LOCAL_CONFIG: $!\n";
	
	my @old_lines = <$icfg>;
	
	close $icfg;
	
	# Go through these lines, substituting the updated configuration setting values. Settings
	# whose values are the same as the default are commented out. That way, if the default
	# value ever changes the change won't be masked.

	# The trick here is that we are modifying YAML formatted data syntactically using a simple
	# state machine. This could potentially cause errors, so we need to be careful.
	
	while ( @old_lines )
	{
	    my $line = shift @old_lines;
	    
	    # If a line is found whose setting name matches something in the updated configuration
	    # data, and we have a defined value for it, substitute the new value if it is
	    # different from the default.
	    
	    if ( $line =~ qr{ ^ ( [#] \s )? (\w+) \s* [:] \s* (.*) $ }xs )
	    {
		my $comment = $2;
		my $key = $2;
		
		# If we are storing a setting value, Use YAML::Tiny to encode the new setting.
		# Then remove any initial line(s) starting with ---. The regex fragment \s ^
		# matches the newline at the end of each matching line, which we want to remove
		# along with the line contents.
		
		if ( $updated{$key} && defined $config_data->{$key} && ! $deprecated_key{$key} )
		{
		    my $new_line = YAML::Tiny::Dump({ $key => $config_data->{$key} });
		    $new_line =~ s/ \A (?: -.* \s ^ )+ //mx;
		    
		    $line = $new_line;
		    $updated_settings++;
		}
		
		# Otherwise, if the line was uncommented, substitute a commented line with the
		# same setting name.
		
		elsif ( $comment eq '' )
		{
		    $line = "# $key: \n";
		}
		
		# Either way, remove this setting from the hash of settings not yet written.
		
		delete $config_data->{$key};
		
		# Remove from the original file contents any subsequent lines that are indented,
		# because as YAML content they encode some previous non-scalar value of the
		# setting we have just replaced.
		
		while ( @old_lines && $old_lines[0] =~ qr{ ^ \s+ [\S] } )
		{
		    shift @old_lines;
		}
	    }
	    
	    # Any other line is left alone.
	    
	    push @config_lines, $line;
	}
    }
    
    # Now go through the remaining configuration settings that weren't written above. Each one
    # that has a value different from the default gets added to the end of the file. But keys
    # which were used by previous versions of this software and are now deprecated are skipped.
    
    foreach my $key ( keys %$config_data )
    {
	if ( defined $config_data->{$key} &&
	     $config_data->{$key} ne $DEFAULT{$key} &&
	     ! $deprecated_key{$key} )
	{
	    $updated_settings++;
	}
	
	else
	{
	    delete $config_data->{$key};
	}
    }
    
    if ( keys %$config_data )
    {
	my $remainder = YAML::Tiny::Dump($config_data);
	$remainder =~ s/ \A (?: -.* \s ^ )+ //mx;
	
	push @config_lines, $remainder;
    }
    
    # Write the new content to disk, but don't overwrite the existing file.
    
    open(my $ocfg, ">", "$LOCAL_CONFIG.new") || die "ERROR: could not write new contents for $LOCAL_CONFIG: $!\n";
    
    print $ocfg @config_lines;
    
    close $ocfg || die "ERROR: could not write new contents for $LOCAL_CONFIG: $!\n";
    
    # Check that the newly written file contains valid YAML. It might actually contain nothing but
    # comments, but it does need to be syntactically valid. If errors are thrown when the content
    # is read back in, rename the new file to the suffix .bad and inform the user.
    
    eval {
	my $new_data = ReadConfigFile("$LOCAL_CONFIG.new", { no_cache => 1 });
    };
    
    if ( $@ )
    {
	move("$LOCAL_CONFIG.new", "$LOCAL_CONFIG.bad");
	
	print "\n$@\n";
	
        print "\nERROR: the newly generated content for $LOCAL_CONFIG was not valid YAML.\n";
	print "\nIf you want to try to fix it, you can edit $LOCAL_CONFIG.bad. If you can\n";
	print "fix the syntax and if it appears to have the content you want, just rename\n";
	print "that file to $LOCAL_CONFIG.\n\n";
	
	exit 2;
    }
    
    # Otherwise, rename the new file over the old one.
    
    move("$LOCAL_CONFIG.new", $LOCAL_CONFIG) || die "ERROR: could not rename $LOCAL_CONFIG.new to $LOCAL_CONFIG: $!\n";
    
    # Remove any .bad file that may have been left lying around from a previous execution.
    
    unlink("$LOCAL_CONFIG.bad");

    # Inform the user of what we did.
    
    print STDOUT "Rewrote $LOCAL_CONFIG, changed $updated_settings settings\n";
}


# RewriteConfigFiles ( files, values, options )
#
# Rewrite the configuration files specified by $files. This can either be 'all' or else an
# arrayref of keys from %CONF_FILE. The argument $values must be a hashref of values to
# substitute. In some cases, it may be a reference to the main %CONFIG hash. The $options argument
# conveys options from the command line.

sub RewriteConfigFiles {
    
    my ($files, $values, $options) = @_;
    
    croak "Bad value '$files' for first argument\n" unless $files eq 'all' || ref $files eq 'ARRAY';
    
    my @file_list = $files eq 'all' ? (@MAIN_CONF, @COMPONENT_CONF) : @$files;
    
    $options ||= { };

    if ( $options->{merge} )
    {
	print "\nAll configuration files which require updating will be rebuilt by merging their\n";
	print "current content with new content rebuilt from the base files.\n\n";
    }
    
    elsif ( $options->{rebuild} )
    {
	print "\nAll configuration files which require updating will be rebuilt from the base files.\n\n";
    }
    
    # For each of the files to be updated, read in the contents and then process the substitutions
    # one by one. If anything has changed, write the updated content back to the file. If any of
    # the base files is newer than the corresponding configuration file, the file will need to be
    # rebuilt from the updated base.
    
    my %rebuild_service;
    
 FILE:
    foreach my $entry ( @file_list )
    {
	# Skip any file associated with a non-included component. But update files for components
	# that exist but are not currently selected.
	
	my $component = $entry->{component};
	
	next unless $component eq 'main' ||
	    $COMPONENT{$component}{path} && -d $COMPONENT{$component}{path};
	
	# Then look at the other file attributes.
	
	my $subst = $entry->{subst};
	my $filename = $entry->{filename};
	my $basename = $entry->{basename};
	my $service = $entry->{service};
	
	my $subst_count = 0;
	
	if ( ref $subst eq 'HASH' && %$subst )
	{
	    foreach my $setting ( keys %$subst )
	    {
		$subst_count++ if defined $values->{$setting};
	    }
	}
	
	elsif ( ref $subst eq 'ARRAY' && @$subst )
	{
	    foreach my $p ( @$subst )
	    {
		my $setting = $p->{setting};
		$subst_count++ if defined $values->{$setting};
	    }
	}
	
	# Determine the method by which we will update this file. The three possibilities are:
	# 
	#  keep     substitute new values into the current file content
	# 
	#  rebuild  substitute new values into the base file content, discard the current file
	#           content
	# 
	#  merge    substitute new values into the base file content and merge the result with the
	#           current file content
	# 
	# If the active file is newer than the base file, we use 'keep' unless --rebuild or
	# --merge was specified on the command line in which case the corresponding method is
	# forced.
	# 
	# If the base file is newer, check to see if the string "MERGE_CONTENT=1" appears
	# somewhere in the first 250 characters of the file. If it does, then 'merge' is
	# used. Otherwise, we choose 'rebuild'. If the site administrator wishes to make manual
	# edits to one or more project configuration files, they should add this string to a
	# comment at the beginning of the file.
	
	my $build_method = "keep";
	
	if ( $options->{merge} )
	{
	    $build_method = 'merge';
	}
	
	elsif ( $options->{rebuild} || -M $basename && -M $filename && -M $basename < -M $filename )
	{
	    $build_method = 'rebuild';
	    
	    my ($fh, $beginning_stuff);
	    
	    if ( open($fh, '<', $filename) && read($fh, $beginning_stuff, 250) )
	    {
		if ( $beginning_stuff =~ qr{ MERGE_CONTENT \s* = \s* 1 }xm )
		{
		    $build_method = 'merge';
		}
	    }
	}
	
	# If the build method is 'keep' and there are no substitutions to be made, we can just
	# skip this file.
	
	if ( $build_method eq 'keep' && $subst_count == 0 )
	{
	    print STDOUT "No changes were made to $filename\n";
	    next FILE;
	}
	
	# If we get here, we need to generate new file content. Start with the content of either
	# the base file or the active file (depending on the build method) as an array of
	# lines. If the original file does not exist, use the base file.
	
	my $sourcename = $basename;
	
	if ( $build_method eq 'keep' && -e $filename && -s $filename )
	{
	    $sourcename = $filename;
	}
	
	my @content = ReadConfigRaw($sourcename);
	
	# For now, we just skip files that can't be read. That is probably not the right approach
	# in the long run.
	
	unless ( @content )
	{
	    print "WARNING: $sourcename was SKIPPED because it could not be read or is empty.\n";
	    next FILE;
	}
	
	# Otherwise, we go through the substitutions one by one. For each substitution, we will
	# scan through the @content array looking for lines which match it. But skip any
	# substitution whose pattern is undefined, because those will be taken care of by other
	# multiline substitutions in the same set.
	
	my $replacement_count = 0;
	
	if ( ref $subst eq 'ARRAY' )
	{
	    foreach my $params ( @$subst )
	    {
		$replacement_count += MakeSubstitution($params, $values, \@content, $filename);
	    }
	}
	
	elsif ( ref $subst eq 'HASH' )
	{
	    foreach my $s ( keys %$subst )
	    {
		my $params = { setting => $s, pattern => $subst->{$s} };
		$replacement_count += MakeSubstitution($params, $values, \@content, $filename);
	    }
	}
	
	# If the build method is 'rebuild', write out the newly generated content to the actual
	# configuration file regardless of the number of substitutions made. Even if there aren't
	# any substitutions, we want the active content to reflect the base content which may have
	# changed since the file was last generated.
	
	if ( $build_method eq 'rebuild' )
	{
	    WriteConfigRaw($filename, \@content);
	    print STDOUT "Generated $filename from $basename, substituted $replacement_count lines\n";
	    
	    $rebuild_service{$service} = 1 if $service;
	}
	
	# If build method is 'merge', write out a temporary file and run diff3 on it. Do this in
	# an eval, so we can clean up if anything goes wrong.
	
	elsif ( $build_method eq 'merge' )
	{
	    my $quit;
	    
	    # Invoke the same editor as git, if we can determine what that is. As a fallback, check
	    # for the environment variables 'VISUAL' and 'EDITOR'.
	    
	    my $editor = CaptureCommand('git', 'var', 'GIT_EDITOR') || $ENV{VISUAL} || $ENV{EDITOR};
	    chomp $editor;
	    
	    unless ( $editor )
	    {
		print "\nERROR: please set the environment variable VISUAL to your preferred editor and try again.\n\n";
		exit 2;
	    }
	    
	    my $new_filename = "$filename.new";
	    my $merge_filename;
	    
	    eval {

		# Write out the rebuilt content to a temporary file.
		
		WriteConfigRaw($new_filename, \@content);
		
		print "Generated $new_filename from $basename, substituted $replacement_count lines\n";
		
		# Then run diff3 with the -m option to merge the new content with the current
		# content. The -E option specifies to add bracketing lines around any changes that
		# cannot be merged. The base file is the middle argument, and the changes between
		# it and the new content will be merged with the changes between it and the
		# current content.
		
		my @merge_lines = CaptureCommand('diff3', '-mE', "$filename.new", $basename, $filename);
		
		# If we detect one or more of the bracketing lines, then there are incompatible
		# changes. Ask the user if they want to fix them manually.
		
		my $edits;
		
		while ( grep /^<<<<<<<|^=======|^>>>>>>>/, @merge_lines )
		{
		    my $question = $edits ? "There are still unmerged changes. Edit again? (y/n/q)"
			: "The new content and current content must be manually merged.\n" .
			  "Do you want to edit the file? (y/n/q)";
		    
		    my $answer = AskQuestion($question, { yesnoquit => 1 });
		    
		    # If the answer is 'yes', write the incompletely merged content to a temporary
		    # file and invoke the editor program.
		    
		    if ( $answer eq 'yes' )
		    {
			unless ( $merge_filename )
			{
			    $merge_filename = "$filename.merge";
			    WriteConfigRaw($merge_filename, \@merge_lines);
			}
			
			my $success = SystemCommand($editor, $merge_filename);
			
			unless ( $success )
			{
			    my $rc = ResultCode();
			    die "ERROR: could not execute '$editor', result code was $rc\n";
			}
			
			# After the editor exits, read the results and loop back again to check
			# for the presence of bracketing lines.

			$edits++;
			
			@merge_lines = ReadConfigRaw($merge_filename);
		    }
		    
		    # Otherwise, abort the merge.

		    else
		    {
			$quit = 1 if $answer eq 'quit';
			print "\n$filename is unchanged\n\n";
			
			unlink $merge_filename if $merge_filename;
			
			return; # exit the eval
		    }
		}
		
		# If we get here, we have a (potentially) good version of the content.
		
		unlink $merge_filename if $merge_filename;
		
		my $answer = AskQuestion("Install merged content as $filename? (y/n/q)",
				         { yesnoquit => 1 });
		
		if ( $answer eq 'yes' )
		{
		    WriteConfigRaw($filename, \@merge_lines);
		    print "\nWrote merged content to $filename\n\n";
		    
		    $rebuild_service{$service} = 1 if $service;
		}

		else
		{
		    print "\n$filename is unchanged\n\n";
		    utime undef, undef, $filename;
		}
	    };

	    # Remove our temporary files. If an exception occurred, re-throw it.
	    
	    unlink $new_filename;
	    unlink $merge_filename if $merge_filename;
	    
	    if ( $@ )
	    {
		die $@;
	    }
	    
	    # Otherwise, either quit (if the user answered q) or go on to the next file.
	    
	    if ( $quit )
	    {
		exit 2;
	    }
	    
	    next FILE;
	}
	
	# Otherwise, the build method must be 'keep'. If we made at least one replacement then
	# write out the file. Flag the associated service for rebuilding, so that the container
	# image will have the updated configuration.
	
	elsif ( $replacement_count > 0 )
	{
	    WriteConfigRaw($filename, \@content);
	    print STDOUT "Rewrote $filename, changed $replacement_count lines\n";
	    
	    $rebuild_service{$service} = 1 if $service;
	}
	
	# If we didn't make any replacements, nothing needs to be changed.
	
	else
	{
	    print STDOUT "No changes were made to $filename\n";
	}
    }
    
    print "\n";
    
    # If this is an update operation rather than an install step, rebuild any services whose
    # configuration has changed.
    
    if ( ($options->{update} || $options->{reset}) && %rebuild_service )
    {
	RebuildContainers(\%rebuild_service);
    }
}


# MakeSubstitution ( params, values, content, filename )
# 
# Make the substitution specified by $params using the values contained in the hashref $values, on
# the elements of the arrayref $content. In each case, the substitution is made at most once, on the
# first matching line. Returns the number of lines changed.

sub MakeSubstitution {

    my ($params, $values, $content, $filename) = @_;
    
    # Skip any substitution for which the pattern is undefined. These will be taken care of by
    # other multi-value substitutions in the same set.
    
    return 0 unless defined $params->{pattern};
    
    # The accepted parameters are:
    # 
    # setting       Specifies the setting whose value is to be inserted
    # pattern       Selects the line on which the value is to be placed
    # all           If true, inserts value on all matching lines rather than just the first one
    # after         If non-empty, the substitution is done after a line matching this regex
    
    my $setting = $params->{setting};
    my $value = $values->{$setting};
    my $pattern = $params->{pattern};
    my $all = $params->{all};
    my $after_regex = $params->{after} ? qr{$params->{after}} : undef;
    
    # Generate a search regex based on the specified pattern. All of these patterns accept
    # arbitrary amounts of whitespace at the beginning of the line.
    
    my $regex;
    my $multivalue;
    
    # A pattern the looks like 'foo:' matches a line that looks like:
    #       foo: xxx
    # or   "foo" : "xxx"
    
    if ( $pattern =~ / ^ ([\w.]+) [:] $ /xs )
    {
	$regex = qr{ ^ ( \s* ["']? $1 ["']? \s* : \s* ) (.*) }xs;
    }
    
    # A pattern that looks like 'foo=' matches a line that looks like:
    #    foo=xxx
    # or foo = 'xxx'
    
    elsif ( $pattern =~ / ^ ([\w.]+) [=] $ /xs )
    {
	$regex = qr{ ^ ( \s* $1 \s* = \s* ) (.*) }xs;
    }
    
    # A pattern that looks like 'foo;' matches a line that looks like:
    #     foo xxx
    # or  foo xxx;
    
    elsif ( $pattern =~ / ^ ([\w.]+) ; $ /xs )
    {
	$regex = qr{ ^ ( \s* $1 \s+ ) (.*) }xs;
    }

    # A pattern that looks like 'foo:[' matches a line that looks like:
    #      foo:
    # or  "foo":
    #
    # and then makes multiple substitutions on subsequent lines. There are only a few of these,
    # and they are hard-coded.
    
    elsif ( $pattern =~ / ^ (\w+) : \[ $ /xs )
    {
	$regex = qr{ ^ ( \s* ["'] $1 ["'] \s* : \s* ) (.*) }xs;
	$multivalue = $setting;
    }
    
    # The following should only happen due to an error in the configuration file entries at the
    # top of this module file or in one of the component-data.yml files.
    
    else
    {
	print "WARNING: unrecognized substitution metapattern '$pattern'\n";
	return 0;
    }
    
    # Skip any single-value substitution if the value to be inserted is undefined.
    
    return 0 unless $multivalue || defined $value;
    
    # Otherwise, search through the content until we find a matching line.
    
    my $replacement_count = 0;
    my $matched_after;
    my $matched_pattern;
    
  LINE:
    foreach my $line_no (0..$#$content)
    {
	# If an 'after' expression was given, skip until we come to a line that matches it.
	
	if ( $after_regex && ! $matched_after )
	{
	    $matched_after = 1 if $content->[$line_no] =~ $after_regex;
	    next LINE;
	}
	
	# Then skip until we come to a line that matches the substitution pattern.
	
        next LINE unless $content->[$line_no] =~ $regex;
	
	# If this is a multi-value substitution, deal with it appropriately. These are all
	# hard-coded.
	
	# The multi-value substitution for pbdb_username and pbdb_password is done in the
	# wing configuration file. The second line after the matching one gets the
	# username, and the third line gets the password.
	
	if ( $multivalue eq 'pbdb_username' )
	{
	    my $space = '      ';
	    my $quote = '"';
	    
	    if ( $content->[$line_no+2] =~ qr{ ^ (\s*) ( ['"] ) }xs )
	    {
		$space = $1;
		$quote = $2;
	    }
	    
	    if ( defined $values->{pbdb_username} )
	    {
		my $new_line = "$space$quote$values->{pbdb_username}$quote,\n";
		
		if ( $new_line ne $content->[$line_no+2] )
		{
		    $content->[$line_no+2] = $new_line;
		    $replacement_count++;
		}
	    }
	    
	    if ( defined $values->{pbdb_password} )
	    {
		my $new_line = "$space$quote$values->{pbdb_password}$quote,\n";
		
		if ( $new_line ne $content->[$line_no+3] )
		{
		    $content->[$line_no+3] = $new_line;
		    $replacement_count++;
		}
	    }
	    
	    $matched_pattern = 1;
	    last LINE;
	}
	
	# The multi-value substitution for smtp_host and smtp_port is also done in the
	# Wing configuration file. We search for lines matching "host" and "port" after
	# the original matching line and before a line that starts with }.
	
	elsif ( $multivalue eq 'smtp_host' )
	{
	    my $quote = '"';
	    
	    foreach my $i ( $line_no+1..$line_no+10 )
	    {
		last if $content->[$i] =~ qr{ ^ \s* \} }xs;
		
		if ( $content->[$i] =~ qr{ ^ ( \s* ["']? host ["']? \s* : \s* ) (.*) }xs )
		{
		    my $space = $1;
		    my $old_value = $2;
		    my ($final) = $2 =~ /(,)$/;
		    my $new_line = "$space$quote$values->{smtp_host}$quote$final\n";
		    
		    if ( defined $values->{smtp_host} && $new_line ne $content->[$i] )
		    {
			$content->[$i] = $new_line;
			$replacement_count++;
		    }
		    
		    $matched_pattern = 1;
		}
		
		elsif ( $content->[$i] =~ qr{ ^ ( \s* ["']? port ["']? \s* : \s* ) (.*) }xs )
		{
		    my $space = $1;
		    my $old_value = $2;
		    my ($final) = $2 =~ /(,)$/;
		    my $new_line = "$space$quote$values->{smtp_port}$quote$final\n";
		    
		    if ( defined $values->{smtp_port} && $new_line ne $content->[$i] )
		    {
			$content->[$i] = $new_line;
			$replacement_count++;
		    }
		    
		    $matched_pattern = 1;
		}
	    }

	    last LINE;
	}
	
	elsif ( $multivalue )
	{
	    print STDOUT "WARNING: unrecognized multivalue setting '$multivalue'\n";
	    return 0;
	}
	
	# Otherwise, construct a simple substitution line. But only increment the substitution
	# count if the new line differs from the existing one.
	
	my $key_part = $1;
	my $value_part = $2;
	
	chomp $key_part;
	
	# If the value part of the existing line starts with ' or ", then quote the
	# new value similarly.
	
	if ( $value_part =~ / ^ (['"]) /xs )
	{
	    $value = "$1$value$1";
	}
	
	# If the value part of the existing line ends in a comma or a semicolon, add that on as
	# well.
	
	if ( $value_part =~ / ( [,;] ) \s* $ /xs )
	{
	    $value .= $1;
	}
	
	# Construct the new line, and substitute it if it differs from the current one.
	
	my $new_line = "$key_part$value\n";
	
	if ( $new_line ne $content->[$line_no] )
	{
	    $content->[$line_no] = $new_line;
	    $replacement_count++;
	}
	
	$matched_pattern = 1;
	
	# We only make each substitution a maximum of once per file, unless the parameter
	# 'all' was specified.
	
	last LINE unless $all;
    }
    
    # Print out a warning if the pattern was not matched by any line. In either case, return the
    # number of substitutions made.
    
    unless ( $matched_pattern )
    {
	print "WARNING: no substitution was found for '$setting' in $filename\n";
    }
    
    return $replacement_count;
}


# RebuildContainers ( containers, options )
#
# Rebuild all of the containers specified by $containers, which must be a hashref whose keys are
# container names.

sub RebuildContainers {
    
    my ($rebuild_hash, $options) = @_;
    
    my %rebuild = %$rebuild_hash;
    my @last;
    
    # If the option 'pull' is given, then check the registry for updated container images first.

    if ( $options && $options->{pull} )
    {
	
	
    }
    
    # If nginx is on our list to rebuild, do that last. We want all of the proxy services running
    # so that nginx can properly connect to them.
    
    if ( $rebuild{nginx} )
    {
	@last = 'nginx';
	delete $rebuild{nginx};
    }
    
    # Go through the services and rebuild any that were selected.
    
    foreach my $s ( sort(keys %rebuild), @last )
    {
	print "\n";
	my $rebuild = AskQuestion("Rebuild the container for service '$s'?", { yesno => 1, default => 'yes' });
	next unless $rebuild eq 'yes';
	
	BuildImage($s, undef, "--run=restart");
    }
}


# ShowConfigCmd ( options )
#
# Show the configuration settings or the configuration files.

sub ShowConfigCmd {

    my ($options) = @_;

    require YAML::Tiny;
    require File::Temp;
    
    my $subcommand = shift @ARGV;
    
    if ( $subcommand eq 'files' )
    {
	return ShowConfigFilesCmd($options);
    }

    elsif ( defined $subcommand && $subcommand ne '' &&
	    $subcommand ne 'settings' && $subcommand ne 'all' )
    {
	print "ERROR: unknown subcommand '$subcommand'\n";
	exit 2;
    }
    
    my @setting;
    my @note;
    my @value;
    
    my $show_all; $show_all = 1 if defined $subcommand && $subcommand eq 'all';
    
    foreach my $key ( sort keys %CONFIG )
    {
	my $value = $CONFIG{$key};
	my $changed = $PMCmd::Config::CONFIG_SET{$key};
	my $same = $CONFIG{$key} eq $DEFAULT{$key};
	
	next unless $show_all || $changed;
	
	if ( ref $value )
	{
	    my $yaml = YAML::Tiny->new($value);
	    my @lines = split /\n/, $yaml->write_string;
	    my $setting = $key;
	    my $note = $changed ? 'struct' : 'default';
	    
	    foreach my $line ( @lines )
	    {
		chomp $line;
		push @setting, $setting;
		push @note, $note;
		push @value, $line;
		$setting = '';
		$note = '';
	    }
	}

	else
	{
	    my $note = $changed ? ($same ? '' : 'unchanged') : 'default';
	    
	    if ( $key =~ /_password/ )
	    {
		$value = '*' x length($value);
	    }
	    
	    push @setting, $key;
	    push @note, $note;
	    push @value, $value;
	}
    }
    
    my ($fh, $fname, $cmd);
    
    if ( -t STDOUT && `which less` && ! $options->{noformat} )
    {
	$fh = File::Temp->new();
	$fname = $fh->filename;
	$cmd = 'less';
	$options->{outfh} = $fh;
    }
    
    PrintOutputList($options, ['Setting', 'Notes', 'Value'], \@setting, \@note, \@value);

    if ( $fh )
    {
	close $fh;
	exec($cmd, $fname);
    }
}


sub ShowConfigFilesCmd {
    
    my ($options) = @_;
    
    my $filter = shift @ARGV;
    
    my @component;
    my @service;
    my @attr;
    
    foreach my $entry ( @MAIN_CONF, @COMPONENT_CONF )
    {
	my $component = $entry->{component};
	my $service = $entry->{service};
	my $filename = $entry->{filename};

	next unless $CONFIG{"include_$component"} eq 'yes';
	
	next if $filter && $component ne $filter && $service ne $filter &&
	    $filename !~ /$filter/o && $entry->{basename} !~ /$filter/o;
	
	push @component, $entry->{component}, '';
	push @service, $entry->{service}, '';
	push @attr, "filename: $entry->{filename}", "basename: $entry->{basename}";

	if ( ref $entry->{subst} eq 'HASH' )
	{
	    foreach my $key ( sort keys %{$entry->{subst}} )
	    {
		next if $key eq 'after';
		my $value = $entry->{subst}{$key} || '';

		my $attr = "substitute $key at '$value'";
		$attr .= " [after '$entry->{subst}{after}']" if $entry->{subst}{after};
		
		push @component, '';
		push @service, '';
		push @attr, $attr;
	    }
	}

	elsif ( ref $entry->{subst} eq 'ARRAY' )
	{
	    foreach my $entry ( @{$entry->{subst}} )
	    {
		my $key = $entry->{setting};
		my $value = $entry->{pattern};
		my $after = $entry->{after};
		my $all = $entry->{all};

		my $attr = "substitute $key at '$value'";
		$attr .= " [after '$after']" if $after;
		$attr .= " [all]" if $all;
		
		push @component, '';
		push @service, '';
		push @attr, $attr;
	    }
	}
	
	push @component, '';
	push @service, '';
	push @attr, '';
    }

    PrintOutputList($options, ['Project component', 'Service', 'Description'],
		    \@component, \@service, \@attr);
}


# Step 5 [build] - pull the preload images for the containers used by this project, and then
# build the final images.

sub BuildStep {
    
    my ($options) = @_;
    
    # If this routine was called from 'update codebase', then the set of containers to build is
    # found in %rebuild_container. If that hash is empty, return without doing
    # anything. Otherwise, pull the images for all containers and try to rebuild them all.
    
    my @rebuild;
    
    if ( $options->{update} && $options->{update} eq 'codebase' )
    {
	if ( %rebuild_container )
	{
	    @rebuild = keys %rebuild_container;
	}

	else
	{
	    print "\nNothing to build.\n";
	    return;
	}
    }
    
    # Go through all of the services specified on the command line, or all services if
    # nothing was specified.
    
    my @preloads;
    my @builds;
    
    my @services = GetComposeServices(@rebuild);
    
    my $compose_yaml = GetComposeYAML();
    
    foreach my $service ( @services )
    {
	if ( $compose_yaml->{services}{$service} &&
	     reftype $compose_yaml->{services}{$service} eq 'HASH' )
	{
	    my $entry = $compose_yaml->{services}{$service};
	    
	    if ( $entry->{build} )
	    {
		push @builds, $service;
		
		my $context = $entry->{build}{context} || '.';
		my $dockerfile = $entry->{build}{dockerfile} || 'Dockerfile';
		my $preload_file = "$context/$dockerfile-preload";
		
		if ( -r $preload_file )
		{
		    push @preloads, $service;
		}
	    }
	}
    }
    
    unless ( @preloads )
    {
	print "\nNo matching services were found\n";
	return;
    }
    
    # For each preload image that needs to be fetched, find the component it belongs to and look
    # up the registry for that component.
    
    my @registry_list;
    my %image_list;
    
    foreach my $service ( @preloads )
    {
	my $image_name = join('_', 'paleomacro', $service, 'preload');
	my $registry = $COMPONENT{$service}{registry};

	unless ( $registry )
	{
	    foreach my $component ( @INSTALLED_COMPONENTS )
	    {
		if ( ref $COMPONENT{$component}{images} eq 'ARRAY' )
		{
		    if ( grep { $_ eq $service } @{$COMPONENT{$component}{images}} )
		    {
			$registry = $COMPONENT{$component}{registry};
			last;
		    }
		}
	    }

	    $registry ||= $CONFIG{default_registry};
	}
	
	push @registry_list, $registry unless $image_list{$registry};
	push @{$image_list{$registry}}, $image_name;
    }
    
    # Now go through the list of registries from which we need to fetch images.

    foreach my $registry ( @registry_list )
    {
	PushPullImages('pull', $registry, @{$image_list{$registry}});
    }
    
    # The Dockerfile for nginx must be put together from a template, depending on which project
    # components are included.
    
    my $no_nginx;
    
    if ( ! -M $CONFIG{nginx_dockerfile_template} )
    {
    	print "ERROR: $CONFIG{nginx_dockerfile_template} is missing. The webserver will not be rebuilt.\n";
    	$no_nginx = 1;
    }
    
    # Now go through all of the services for which a build is needed, and build each one. Each
    # build step is wrapped in an eval to make sure that if one fails there is a chance for others
    # to succeed.
    
    my @failed_builds;
    
    foreach my $service ( @builds )
    {
	next if $service eq 'nginx' && $no_nginx;
	
	# If the image already exists and is newer than the preload image, skip it. But not if
	# this routine was run from 'update codebase'.

	unless ( $options->{update} && $options->{update} eq 'codebase' )
	{
	    next if FindBuiltImage($service);
	}
	
	# Otherwise, ask the user if they want to (re)build the container now.
	
	my $build_answer = AskQuestion("Build image 'paleobiodb_$service'?", { yesnoquit => 1, default => 'yes' });
	
	exit if $build_answer =~ /^q/;
	next unless $build_answer =~ /^y/i;
	
	# If this is an update, then the service should be restarted if it is already running.
	
	if ( $options->{update} )
	{
	    my $result = BuildImage($service, undef, "--run=restart");
	    
	    unless ( $result )
	    {
		print "\nThe previous container image remains in place.\n\n";
	    }
	}
	
	# For an install, we want to build the services but not check or run them.
	
	else
	{
	    my $result = BuildImage($service, undef, "--run=nocheck");
	    
	    if ( $result )
	    {
		print "\nBuild succeeded. Service '$service' is ready to go.\n\n";
	    }
	    
	    else
	    {
		print "\nBuild failed.\n\n";
		push @failed_builds, $service;
	    }
	}
    }
    
    # If this is an installation rather than an update and any of the builds failed, then the
    # installation procedure must stop here until the problem is fixed.
    
    if ( @failed_builds )
    {
	my $list = join(', ', @failed_builds);
	print "\nThe following services will not start: $list\n\n";
	print "You will need to find and fix the problem(s), then rerun the\n";
	print "installation command as ./install.pl images.\n";
	exit;
    }
}


# ShowImagesCmd ( )
#
# Show the active project components.

sub ShowImagesCmd {

    my ($options) = @_;

    my $filter = shift @ARGV;
    
    my $pname = $MAIN_NAME;
    
    my @lines = CaptureCommand('docker', 'image', 'ls');
    
    my $header = shift @lines;
    
    # substr($header, 0, 10) = 'IMAGE NAME';
    
    # print $header;
    
    my (@name, @tag, @id, @created, @size);
    
    # Filter for lines that start with the image prefix for this project, as well as those that
    # start with 'paleomacro_' and end with '_preload'. Split each line into five fields separated
    # by sequences of two or more spaces.
    
    foreach my $line ( @lines )
    {
	if ( $line =~ qr{ ^ $pname _ | ^ paleomacro_ .* _preload \s }xs )
	{
	    chomp $line;

	    if ( $filter )
	    {
		next unless $line =~ /$filter/;
	    }
	    
	    my ($name, $tag, $id, $created, $size) = split(/  +/, $line, 5);
	    
	    push @name, $name;
	    push @tag, $tag;
	    push @id, $id;
	    push @created, $created;
	    push @size, $size;
	}
    }

    if ( $filter && @name == 0 )
    {
	print "No images found for '$filter'\n";
	return;
    }

    PrintOutputList($options, ['Image name', 'Tag', 'Image ID', 'Size', 'Created'],
		    \@name, \@tag, \@id, \@size, \@created);
}


# Step 6 [database] - initialize the database management system(s), set the root password and api
# passwords, and execute the necessary SQL statements to prepare the database(s) for use.

sub DatabaseStep {

    my ($options) = @_;
    
    # First determine if a particular database component has been specified. If the value is
    # 'database', then all installed database components should be initialized.
    
    my $component = $options->{install} || $options->{update};
    
    # If the MariaDB component has been installed, then initialize it if the specified component
    # is either 'database' (all database components) or 'mariadb'. If any other component was
    # specified, skip this sub-step.
    
    if ( $CONFIG{include_mariadb} eq 'yes' )
    {
	# If all components are to be initialized, ask the user to confirm that they want to
	# execute the mariadb initialization substep.
	
	my $init_mariadb;
	
	if ( $component eq 'database' )
	{
	    my $label = StepLabel('mariadb');
	    my $rule = '-' x length($label);
	    
	    print "\n$label\n$rule\n";
	    
	    my $dothis = AskQuestion("Execute this substep? (y/n/q) ",
				 { yesnoquit => 1, default => 'yes' });
	    
	    exit if $dothis eq 'quit';
	    
	    if ( $dothis eq 'yes' )
	    {
		$init_mariadb = 1;
	    }
	}
	
	# If only the mariadb component is to be initialized, do it without asking.
	
	elsif ( $component eq 'mariadb' )
	{
	    $init_mariadb = 1;
	}

	if ( $init_mariadb )
	{
	    my $install_module = $COMPONENT{mariadb}{install} || "component/Install_mariadb.pm";
	    require "$MAIN_PATH/$COMPONENT{mariadb}{path}/$install_module";
	    
	    eval {
		PMCmd::Install_mariadb::InitDatabase($options);
	    };
	    
	    if ( $@ )
	    {
		print "\nERROR: an error occurred while initializing mariadb:\n$@\n\n";
	    }
	}
    }
    
    # If the PostgreSQL component has been installed, then initialize it if the specified component
    # is either 'database' (all database components) or 'postgresql'. If any other component was
    # specified, skip this sub-step.
    
    if ( $CONFIG{include_postgresql} eq 'yes' )
    {
	# If all components are to be initialized, ask the user to confirm that they want to
	# execute the postgresql initialization substep.

	my $init_postgresql;
	
	if ( $component eq 'database' )
	{
	    my $label = StepLabel('postgresql');
	    my $rule = '-' x length($label);
	    
	    print "\n$label\n$rule\n";
	    
	    my $dothis = AskQuestion("Execute this substep? (y/n/q) ",
				 { yesnoquit => 1, default => 'yes' });
	    
	    exit if $dothis eq 'quit';
	    
	    if ( $dothis eq 'yes' )
	    {
		system("echo 'postgresql' > .install");
		$init_postgresql = 1;
	    }
	}

	# If only the postgresql component is to be initialized, do it without asking.
	
	elsif ( $component eq 'postgresql' )
	{
	    $init_postgresql = 1;
	}

	if ( $init_postgresql )
	{
	    my $install_module = $COMPONENT{postgresql}{install} || "component/Install_postgresql.pm";
	    require "$MAIN_PATH/$COMPONENT{postgresql}{path}/$install_module";
	    
	    eval {
		PMCmd::Install_postgresql::InitDatabase($options);
	    };
	    
	    if ( $@ )
	    {
		print "\nERROR: an error occurred while initializing mariadb:\n$@\n\n";
	    }
	}
    }
}


# Step 6 [database] update - This function is called via 'pbdb update [database|password|api|exec|root]'.

sub UpdateDatabaseCmd {
    
    my ($options) = @_;
    
    my $step = $options->{update} || return;
    
    my $subcommand = shift @ARGV;
    
    # If the first argument is either 'database', 'postgresql', 'mariadb', or 'mysql' execute the
    # update step specified by the second argument. The argument 'mysql' is taken to be an alias
    # for 'mariadb'. For some subcommands such as 'volume' or 'procedures', if there is more than
    # one database installed then the user will be prompted to specify which one to update. The
    # same passwords are used for all databases, so 'database' is acceptable when updating
    # passwords regardless of whether more than one database is installed.
    
    if ( $step eq 'database' || $step eq 'postgresql' || $step eq 'mariadb' )
    {
	# The 'update database volume' subcommand just runs the appropriate database install step.
	
	if ( $subcommand eq 'volume' )
	{
	    $options->{update} = $step;
	    goto &DatabaseStep;
	}
	
	# All of the password setting subcommands except 'root' call the same routine. We
	# deliberately accept all of the following arrangements:
	# - update database <component> password
	# - update database password <component>
	# - update <component> password (see below)
	# - update password <component> (see below)
	
	elsif ( $subcommand eq 'password' || $subcommand eq 'user' ||
		$subcommand eq 'pbdb' || $subcommand eq 'paleobiodb' ||
		$subcommand eq 'macro' || $subcommand eq 'macrostrat' ||
		$subcommand eq 'rockd' || $subcommand eq 'mibasin' ||
		$subcommand eq 'api' || $subcommand eq 'exec' || $subcommand eq 'root' )
	{
	    UpdateDatabasePassword($step, $subcommand, @ARGV);
	}
	
	# The 'update database procedures' subcommand updates all of the SQL stored procedures
	# necessary for a particular service, or all of them if no services are specified.
	
	elsif ( $subcommand eq 'procedures' )
	{
	    if ( $CONFIG{include_mariadb} eq 'yes' && ($step eq 'database' || $step eq 'mariadb') )
	    {
		my $db_service = $COMPONENT{mariadb}{service} || 'mariadb';
		my $db_container = $COMPONENT{mariadb}{container} || "${MAIN_NAME}_${db_service}_1";
		
		my $install_module = $COMPONENT{mariadb}{install} || "component/Install_mariadb.pm";
		require "$MAIN_PATH/$COMPONENT{mariadb}{path}/$install_module";
		
		PMCmd::Install_mariadb::InstallProcedures($db_container, @ARGV);
	    }
	    
	    else
	    {
		print "\nNothing to update.\n\n";
	    }
	}
	
	# The 'update database schema' subcommand loads DBVersion.pm, and then calls its main
	# subroutine. We don't load that module unless this function is invoked, or during
	# installation after database contents are loaded.

	elsif ( $subcommand eq 'schema' )
	{
	    if ( $CONFIG{include_mariadb} eq 'yes' && ($step eq 'database' || $step eq 'mariadb') )
	    {
		require "PMCmd/DBVersion.pm";
		
		my $dbname = shift @ARGV;
		
		PMCmd::DBVersion::UpdateDatabaseSchema($dbname);
		
		print "\nDone.\n";
	    }
	    
	    else
	    {
		print "Nothing to update.\n";
	    }
    	}
	
	# The 'update database content' subcommand just runs the 'content' install step.
	
	elsif ( $subcommand eq 'content' )
	{
	    $options->{update} = 'content';
	    goto &ContentStep;
	}
	
	# Otherwise, print out documentation.
	
	elsif ( $subcommand )
	{
	    print "ERROR: unrecognized subcommand 'update database $subcommand'.\n";
	    print HelpString('update', 'database');
	}
	
	else
	{
	    print "ERROR: you must provide a subcommand to 'update database'.\n";
	    print HelpString('update', 'database');
	}
    }
    
    # If the argument is either 'password', 'api', 'exec', or 'root', then update the specified
    # database password.
    
    elsif ( $subcommand eq 'password' || $subcommand eq 'user' ||
	    $subcommand eq 'pbdb' || $subcommand eq 'paleobiodb' ||
	    $subcommand eq 'macro' || $subcommand eq 'macrostrat' ||
	    $subcommand eq 'rockd' || $subcommand eq 'mibasin' ||
	    $subcommand eq 'api' || $subcommand eq 'exec' || $subcommand eq 'root' )
    {
	UpdateDatabasePassword($step, $subcommand, @ARGV);
    }
    
    else
    {
	die "ERROR: unrecognized subcommand 'update $step'.\n";
    }
}


# UpdateDatabasePassword ( component, which, second )
#
# Update one of the database passwords, either 'api', 'exec', or 'root'. This can be specified
# either by the first word or the second. If the first word is 'password', then the second word
# must be one of these three.

my %LABEL = ( 'pbdb' => 'database password for the paleobiodb component',
	      'paleobiodb' => 'database password for the paleobiodb component',
	      'macro' => 'database password for the macrostrat component',
	      'macrostrat' => 'database password for the macrostrat component',
	      'rockd' => 'database password for the rockd component',
	      'mibasin' => 'database password for the mibasin component',
	      'mibas' => 'database password for the mibasin component',
	      'exec' => 'database executive password',
	      'root' => 'database root password' );

my %PASSWORD_VAR_MAP = ( paleobiodb => 'pbdb',
			 macrostrat => 'macro',
			 mibasin => 'mibas',
			 rockd => 'rockd' );

my %PASSWORD_COMPONENT_MAP = ( pbdb => 'paleobiodb',
			       macro => 'macrostrat',
			       mibas => 'mibasin',
			       rockd => 'rockd' );

sub UpdateDatabasePassword {
    
    my ($dbcomponent, $which, $second) = @_;
    
    my $mode;
    
    # First figure out which password we are updating. This might be specified by either the first
    # or the second argument.
    
    if ( $which eq 'password' || $which eq 'user' )
    {
	$mode = $which;
	
	if ( $LABEL{$second} )
	{
	    $which = $second;
	}
	
	elsif ( $second )
	{
	    print "ERROR: '$second' is not a recognized database role.\n";
	    return;
	}
	
	else
	{
	    print "ERROR: you must specify which password to update.\n";
	    return;
	}
    }
    
    elsif ( $LABEL{$which} && $second )
    {
	$mode = $second;
	die "ERROR: unrecognized subcommand 'update $which $second'.\n"
	    unless $second eq 'password' || $second eq 'user';
    }
    
    else
    {
	die "ERROR: unrecognized subcommand 'update $which'.\n";
    }
    
    # If we are updating 'root', then it is necessary for a particular database to be specified if
    # more than one is installed. For all of the other passwords, the database component name is
    # ignored and the passwords are set identically in all installed database components.
    
    if ( $which eq 'root' )
    {
	SetDatabaseRootPassword($dbcomponent);
	return;
    }

    else
    {
	foreach my $dbcomponent ( @DB_COMPONENTS )
	{
	    my $install_module = $COMPONENT{$dbcomponent}{install} || "component/Install_$dbcomponent.pm";
	    require "$MAIN_PATH/$COMPONENT{$dbcomponent}{path}/$install_module";
	}
    }
    
    # If we are updating 'api', then we ask for a new password for each installed component that
    # has an updatable password. If we are updating 'exec', then we ask for a new executive
    # username and/or password and then update the access privileges for each component.
    
    my (@update_list, %substitute, $currentexecuser, $currentexecpw, $newexecuser, $newexecpw);
    
    if ( $which eq 'api' || $which eq 'exec' )
    {
	foreach my $compname ( qw(paleobiodb macrostrat rockd mibasin) )
	{
	    if ( $CONFIG{"include_$compname"} eq 'yes' )
	    {
		push @update_list, $compname;
	    }
	}
	
	if ( $which eq 'exec' )
	{
	    unshift @update_list, 'exec';
	    
	    $currentexecuser = $CONFIG{exec_username};
	    $currentexecpw = $CONFIG{exec_password};
	    
	    $newexecuser = AskQuestion("New executive username?", { default => $currentexecuser });
	    $newexecpw = AskQuestion("New executive password?", { default => $currentexecpw });
	    
	    unless ( $newexecpw && $newexecuser && ($newexecpw ne $currentexecpw ||
						    $newexecuser ne $currentexecuser ||
						    $mode eq 'user') )
	    {
		print "\nNothing was changed.\n\n";
		return;
	    }
	    
	    if ( $newexecpw =~ /[']/ )
	    {
		print "\nInvalid password. Passwords must not contain single-quote marks.\n\n";
		return;
	    }

	    $substitute{exec_username} = $newexecuser;
	    $substitute{exec_password} = $newexecpw;
	}
    }
    
    # Otherwise, we check to see if the specified component is actually included in this
    # installation. If it is, we update the corresponding settings and the user passwords for all
    # installed database components.
    
    else
    {
	my $compname = $PASSWORD_COMPONENT_MAP{$which} || $which;
	
	if ( $CONFIG{"include_$compname"} eq 'yes' )
	{
	    push @update_list, $compname;
	}

	elsif ( $compname eq 'exec' )
	{
	    push @update_list, $compname;
	}
	
	else
	{
	    print "\nThe $compname component is not included in this installation.\n\n";
	    return;
	}
    }
    
    # Now we go through each of the specified components and update the corresponding username and
    # password. We rewrite the configuration files each time even if there is more than one
    # password to update. The reason for this is so that if the user terminates the process after
    # one of the prompts is given, the values in the configuration files are in almost all cases
    # going to match the values set in the database.

    my %substitute;
    
    foreach my $compname ( @update_list )
    {
	my $varname = $PASSWORD_VAR_MAP{$compname} || $compname;

	my ($currentuser, $currentpw, $newuser, $newpw);
	
	if ( $which eq 'exec' )
	{
	    $currentuser = $currentexecuser;
	    $currentpw = $currentexecpw;
	    
	    $newuser = $newexecuser;
	    $newpw = $newexecpw;
	}
	
	else
	{
	    $currentuser = $CONFIG{"${varname}_username"};
	    $currentpw = $CONFIG{"${varname}_password"};
	    
	    $newuser = AskQuestion("New api username for the $compname component?",
			       { default => $currentuser });
	    $newpw = AskQuestion("New api password for the $compname component?",
			     { default => $currentpw });
	    
	    unless ( $newpw && $newuser && ($newpw ne $currentpw ||
					    $newuser ne $currentuser ||
					    $mode eq 'user') )
	    {
		print "\nNothing was changed.\n\n";
		next;
	    }
	    
	    if ( $newpw =~ /[']/ )
	    {
		print "\nInvalid password. Passwords must not contain single-quote marks.\n\n";
		next;
	    }
	    
	    $substitute{"${varname}_username"} = $newuser;
	    $substitute{"${varname}_password"} = $newpw;
	}
	
	# If we get here, then we have something to change. Go through all installed database
	# components and make the necessary change.

	foreach my $dbcomponent ( @DB_COMPONENTS )
	{
	    no strict 'refs';

	    eval {
		if ( $which eq 'exec' && $compname ne 'exec' )
		{
		    &{"PMCmd::Install_${dbcomponent}::SetUserAccess"}($newuser, $compname, 'exec');
		    # PMCmd::Install_mariadb::SetUserAccess($newuser, $compname, 'exec');
		}
		
		elsif ( $mode eq 'user' || $newuser ne $currentuser )
		{
		    &{"PMCmd::Install_${dbcomponent}::CreateDatabaseUser"}($newuser, $newpw, 'api');
		    # PMCmd::Install_mariadb::CreateDatabaseUser($newuser, $newpw, 'api');
		    
		    if ( $currentuser && $newuser ne $currentuser )
		    {
			&{"PMCmd::Install_${dbcomponent}::DeleteDatabaseUser"}($currentuser, $newuser);
			# PMCmd::Install_mariadb::DeleteDatabaseUser($currentuser, $newuser);
		    }
		    
		    if ( $which ne 'exec' )
		    {
			&{"PMCmd::Install_${dbcomponent}::SetUserAccess"}($newuser, $compname, 'api');
			# PMCmd::Install_mariadb::SetUserAccess($newuser, $compname, 'api');
		    }
		}
		
		else
		{
		    &{"PMCmd::Install_${dbcomponent}::SetUserPassword"}($newuser, $newpw);
		    # PMCmd::Install_mariadb::SetUserPassword($newuser, $newpw);
		}
	    };
	    
	    if ( $@ )
	    {
		print "\nERROR: an error occurred while changing '$newuser' in $dbcomponent:\n";
		print "$@\n\n";
	    }
	}
	
	# if ( $CONFIG{include_mariadb} eq 'yes' )
	# {
	#     my $install_module = $COMPONENT{mariadb}{install} || "component/Install_mariadb.pm";
	#     require "$MAIN_PATH/$COMPONENT{mariadb}{path}/$install_module";
	    
	#     if ( $which eq 'exec' && $compname ne 'exec' )
	#     {
	# 	PMCmd::Install_mariadb::SetUserAccess($newuser, $compname, 'exec');
	#     }
	    
	#     elsif ( $mode eq 'user' || $newuser ne $currentuser )
	#     {
	# 	PMCmd::Install_mariadb::CreateDatabaseUser($newuser, $newpw, 'api');
		
	# 	if ( $currentuser && $newuser ne $currentuser )
	# 	{
	# 	    PMCmd::Install_mariadb::DeleteDatabaseUser($currentuser, $newuser);
	# 	}
			  
	# 	if ( $which ne 'exec' )
	# 	{
	# 	    PMCmd::Install_mariadb::SetUserAccess($newuser, $compname, 'api');
	# 	}
	#     }
	    
	#     else
	#     {
	# 	PMCmd::Install_mariadb::SetUserPassword($newuser, $newpw);
	#     }
	# }
	
	# if ( $CONFIG{include_postgresql} eq 'yes' )
	# {
	#     my $install_module = $COMPONENT{postgresql}{install} || "component/Install_postgresql.pm";
	#     require "$MAIN_PATH/$COMPONENT{postgresql}{path}/$install_module";
	    
	#     if ( $which eq 'exec' && $compname ne 'exec' )
	#     {
	# 	PMCmd::Install_postgresql::SetUserAccess($newuser, $compname, 'exec');
	#     }
	    
	#     elsif ( $mode eq 'user' || $newuser ne $currentuser )
	#     {
	# 	PMCmd::Install_postgresql::CreateDatabaseUser($newuser, $newpw, 'api');
		
	# 	if ( $currentuser && $newuser ne $currentuser )
	# 	{
	# 	    PMCmd::Install_postgresql::DeleteDatabaseUser($currentuser, $newuser);
	# 	}
		
	# 	if ( $which ne 'exec' )
	# 	{
	# 	    PMCmd::Install_postgresql::SetUserAccess($newuser, $compname, 'api');
	# 	}
	#     }
	    
	#     else
	#     {
	# 	PMCmd::Install_postgresql::SetUserPassword($newuser, $newpw);
	#     }
	# }
    }
    
    # Substitute the new username(s) and password(s) in the main configuration file and all
    # service configuration files.
    
    RewriteLocalConfig(\%substitute);
    RewriteConfigFiles('all', \%substitute, { update => 1 });
}


sub SetDatabaseRootPassword {

    my ($dbcomponent) = @_;
    
    if ( $dbcomponent eq 'database' )
    {
	if ( $CONFIG{include_mariadb} eq 'yes' && $CONFIG{include_postgresql} eq 'yes' )
	{
	    print "\nYou must specify which root password to update: mariadb or postgresql\n\n";
	    exit;
	}
	
	elsif ( $CONFIG{include_mariadb} eq 'yes' )
	{
	    $dbcomponent = 'mariadb';
	}
	
	elsif ( $CONFIG{include_postgresql} eq 'yes' )
	{
	    $dbcomponent = 'postgresql';
	}
	
	else
	{
	    print "\nNo database components are installed.\n\n";
	}
    }
    
    elsif ( $dbcomponent eq 'mariadb' )
    {
	unless ( $CONFIG{include_mariadb} eq 'yes' )
	{
	    print "\nThe mariadb database component is not installed.\n\n";
	    return;
	}
    }
    
    elsif ( $dbcomponent eq 'postgresql' )
    {
	unless ( $CONFIG{include_postgresql} eq 'yes' )
	{
	    print "\nThe postgresql database component is not installed.\n\n";
	    return;
	}
    }
    
    else
    {
	print "\nUnknown database component: $dbcomponent\n\n";
	return;
    }
    
    my $newpw = AskPassword("New $dbcomponent root password: ");
    
    unless ( $newpw )
    {
	print "\nNo password was entered.\n\n";
	exit;
    }
    
    if ( $newpw =~ /['\s]/ )
    {
	print "\nPlease choose a password without quote marks or whitespace.\n\n";
	exit;
    }
    
    my $newpw2 = AskPassword("New password again: ");
    
    unless ( $newpw2 && $newpw2 eq $newpw )
    {
	print "\nThe two passwords did not match.\n\n";
	exit;
    }
    
    # Now set the password.
    
    my $install_module = $COMPONENT{$dbcomponent}{install} || "component/Install_$dbcomponent.pm";
    require "$MAIN_PATH/$COMPONENT{$dbcomponent}{path}/$install_module";
    
    no strict 'refs';
    
    my $result = &{"PMCmd::Install_$dbcomponent::SetRootPassword"}($newpw);
        
    if ( $result )
    {
	print "\nThe root password for $dbcomponent has been changed.\n\n";
    }
    
    else
    {
	print "\nPassword was not changed.\n\n";
    }
}


my @PBDB_PIECE = ( pbdb => "the database 'pbdb'",
		   pbdb_wing => "the database 'pbdb_wing'",
		   database => "the database 'pbdb' and 'pbdb_wing'",
		   images => "the paleobiodb images directory",
		   archives => "the paleobiodb archives directory",
		   aux => "the paleobiodb images and archives directories",
		   macrostrat => "the database 'macrostrat'",
		   all => "all paleobiodb content for a local site",
		   datalogs => "the paleobiodb datalogs directory",
		   master => "all paleobiodb content for the master site" );

my %PBDB_PIECE = @PBDB_PIECE;

my %PBDB_COMPOSITE = ( 'database' => 'pbdb pbdb_wing',
		       'aux' => 'images archives',
		       'all' => 'pbdb pbdb_wing images archives macrostrat',
		       'master' => 'pbdb pbdb_wing images archives datalogs macrostrat' );

my @PBDB_LOCAL = qw(pbdb pbdb_wing images archives macrostrat);
my @PBDB_FULL = qw(pbdb pbdb_wing images archives datalogs macrostrat);

my @MACRO_PIECE = ( macrostrat => "the database 'macrostrat'",
		    all => "all macrostrat content for a local site",
		    master => "all macrostrat content for the master site" );

my %MACRO_PIECE = @MACRO_PIECE;

my %MACRO_COMPOSITE = ( 'all' => 'macrostrat',
			'master' => 'macrostrat' );

my @MACRO_LOCAL = qw(macrostrat);
my @MACRO_FULL = qw(macrostrat);

my %REMOTE_SOURCE = ( pbdb => 'pbdb', pbdb_wing => 'pbdb',
		      images => 'pbdb', archives => 'pbdb', datalogs => 'pbdb',
		      macrostrat => 'macrostrat' );

my %REMOTE_NAMES = ( pbdb => ['pbdb-latest.gz', 'pbdb-backup-latest.gz'],
		     pbdb_wing => ['pbdb-wing-latest.gz', , 'pbdb-wing-backup-latest.gz'],
		     macrostrat => ['macrostrat-latest.gz', 'macrostrat-backup.gz',
				   'macrostrat-backup-latest.gz', 'macrostrat.gz'],
		     images => ["*.png"],
		     archives => ["*.header"],
		     datalogs => ["datalog-*"] );

our %LOCAL_NAME = ( pbdb => 'pbdb-latest.gz',
		    pbdb_wing => 'pbdb-wing-latest.gz',
		    macrostrat => 'macrostrat-latest.gz',
		    images => 'pbdb-images.tgz',
		    archives => 'pbdb-archives.tgz',
		    datalogs => 'pbdb-datalogs.tgz' );

# Step 7 [content] - load the initial database contents, either from a remote site or from files.

sub ContentStep {

    my ($options) = @_;
    
    # Check for options after the step name.
    
    my ($opt_auto, $opt_remote, $opt_local, $opt_file, $opt_setdefaults);
    
    GetOptions( 'y|auto' => \$opt_auto,
	        'remote=s' => \$opt_remote,
		'local' => \$opt_local,
		'file=s' => \$opt_file,
	        'set-defaults' => \$opt_setdefaults);
    
    $options->{auto} = 1 if $opt_auto;
    $options->{remote} = $opt_remote if $opt_remote;
    $options->{local} = 1 if $opt_local;
    $options->{file} = $opt_file if $opt_file;
    $options->{setdefaults} = 1 if $opt_setdefaults;
    
    # Read the default settings from the configuration file, if they exist and are non-empty.
    
    my (@pbdb_default_list, @macro_default_list);
    
    if ( $CONFIG{pbdb_default_load} )
    {
	@pbdb_default_list = grep { $PBDB_PIECE{$_} } split /\s+/, $CONFIG{pbdb_default_load};
    }
    
    if ( $CONFIG{macro_default_load} )
    {
	@macro_default_list = grep { $MACRO_PIECE{$_} } split /\s+/, $CONFIG{macro_default_load};
    }
    
    # Set the load mode from the options, or else read from the configuration file. The default
    # mode is 'remote'.
    
    my ($load_mode, $load_source);
    
    if ( $opt_remote )
    {
	$load_mode = 'remote';
	$load_source = $opt_remote;
    }
    
    elsif ( $opt_file || $opt_local )
    {
	$load_mode = 'file';
	$load_source = $opt_file;
    }
    
    else
    {
	$load_mode = $CONFIG{macro_load_mode} || 'remote' if $COMMAND eq 'macrostrat';
	$load_mode = $CONFIG{pbdb_load_mode} || 'remote' if $COMMAND eq 'pbdb';
    }
    
    # If one or more content pieces were specified on the command line, load just those pieces and
    # ignore the default list.
    
    my (@load_pieces, $load_mode, $command_line);
    
    if ( @ARGV )
    {
	foreach my $arg ( @ARGV )
	{
	    if ( $PBDB_PIECE{$arg} || $MACRO_PIECE{$arg} )
	    {
		push @load_pieces, $arg;
	    }

	    else
	    {
		die "ERROR: unknown content piece '$arg'\n";
	    }
	}

	$command_line = 1;
    }
    
    # Otherwise, if this subroutine was invoked using the 'update' subcommand and we have a
    # default list, use that.
    
    elsif ( $options->{update} && $COMMAND eq 'macrostrat' && @macro_default_list )
    {
	@load_pieces = @macro_default_list;
    }

    elsif ( $options->{update} && $COMMAND eq 'pbdb' && @pbdb_default_list )
    {
	@load_pieces = @pbdb_default_list;
    }

    # Otherwise, start with the list of all the pieces corresponding to installed project
    # components. The default mode will be 'remote'.
    
    else
    {
	# The list for macrostrat is currently short, but will expand in the future as this
	# command is refined for the macrostrat project.
	
	if ( $CONFIG{include_macrostrat} eq 'yes' )
	{
	    push @load_pieces, @MACRO_FULL;
	}
	
	# The set of project pieces to load for the paleobiodb project depends on whether this
	# this will be one of the official sites or a local site. This choice was made in the
	# 'config' step above, and is stored in the configuration setting 'pbdb_site'.
	
	if ( $CONFIG{include_paleobiodb} eq 'yes' )
	{
	    if ( $CONFIG{pbdb_site} )
	    {
		push @load_pieces, @PBDB_FULL;
	    }
	    
	    else
	    {
		push @load_pieces, @PBDB_LOCAL;
	    }
	}
    }
    
    $load_mode ||= 'remote';
    
    my $pbdb_remote = $CONFIG{pbdb_master_login} ? $CONFIG{pbdb_master_host}
	: $CONFIG{pbdb_public_host};
    
    my $macro_remote = $CONFIG{macro_master_login} ? $CONFIG{macro_master_host}
	: $CONFIG{macro_public_host};
    
    # Ask the user whether to load this list of pieces. If they answer 'no', they will be asked to
    # choose an alternate list of pieces. Skip this if the --auto option was specified, or if we
    # are loading a single piece from a specified file.
    
    unless ( $options->{auto} || $command_line && $opt_file && @load_pieces == 1 )
    {
	print "\nThe list of content pieces to be loaded is as follows:\n\n";
	
	# If this command is running as 'macrostrat', then the macrostrat label for a given piece
	# takes priority. Otherwise, the pbdb one does.
	
	foreach my $piece ( @load_pieces )
	{
	    my $label = $COMMAND eq 'macrostrat'
		? ($MACRO_PIECE{$piece} || $PBDB_PIECE{$piece})
		: ($PBDB_PIECE{$piece} || $MACRO_PIECE{$piece});
	    
	    print sprintf("  %-15s \%s\n", $piece, $label);
	}

	print "\n";
	
	my $number_label = @load_pieces == 1 ? 'this piece' : 'each of these pieces';
	my $mode_label;
	
	if ( $load_mode eq 'file' && $load_source && @load_pieces == 1 )
	{
	    $mode_label = "from the file $load_source";
	}
	
	elsif ( $load_mode eq 'file' )
	{
	    $mode_label = "from a local file";
	}
	
	elsif ( $load_source )
	{
	    $mode_label = "from the remote server $load_source";
	}
	
	else
	{
	    my ($pbdb_content, $macro_content) = RemoteSelect(@load_pieces);
	    
	    if ( $pbdb_content && $macro_content )
	    {
		print "Paleobiology Database content will be loaded from: $pbdb_remote\n";
		print "Macrostrat content will be loaded from: $macro_remote\n";
	    }

	    elsif ( $pbdb_content )
	    {
		print "This content will be loaded from: $pbdb_remote\n";
	    }

	    elsif ( $macro_content )
	    {
		print "This content will be loaded from: $macro_remote\n";
	    }

	    $mode_label = "from the remote server(s) listed above"
	}
	
	my $answer = AskQuestion("Load ${number_label} ${mode_label}? (y/n/q)",
			         { yesnoquit => 1, default => 'yes' });
	
	return if $answer eq 'quit';
	
	if ( $answer eq 'no' )
	{
	    @load_pieces = ChooseContentPieces($load_mode, $pbdb_remote, $macro_remote, $options);
	}
    }
    
    # Now generate a list of individual pieces to load, splitting up composite ones.
    
    my (@individual, %included, %remote_source);
    
    foreach my $piece ( @load_pieces )
    {
	if ( $COMMAND eq 'macrostrat' && $MACRO_COMPOSITE{$piece} )
	{
	    push @individual, split /\s+/, $MACRO_COMPOSITE{$piece};
	}
	
	elsif ( $COMMAND eq 'pbdb' && $PBDB_COMPOSITE{$piece} )
	{
	    push @individual, split /\s+/, $PBDB_COMPOSITE{$piece};
	}
	
	else
	{
	    push @individual, $piece;
	}
    }
    
    # If we are loading from files, do that now. Remove duplicate entries first. If only one piece
    # is to be loaded and a specific filename was given, that will be used.
    
    if ( $load_mode eq 'file' )
    {
	my (@file_list, %included);
	
	foreach my $piece ( @individual )
	{
	    next if $included{$piece};
	    $included{$piece} = 1;
	    push @file_list, $piece;
	}
	
	LoadContentFromFiles($load_source, \@file_list, $options);
    }
    
    # Otherwise, we are loading from remote sites. Separate the list of pieces to load by remote
    # source and then load from each selected source.
    
    else
    {
	my (%remote_list, %included);
	
	foreach my $piece ( @individual )
	{
	    next if $included{$piece};
	    $included{$piece} = 1;
	    
	    if ( my $source = $REMOTE_SOURCE{$piece} )
	    {
		push @{$remote_list{$source}}, $piece;
	    }
	    
	    else
	    {
		print "WARNING: skipping '$piece', no remote source found\n";
	    }
	}
	
	if ( $remote_list{pbdb} )
	{
	    FetchPaleobiodbContent($remote_list{pbdb}, $options);
	}

	if ( $remote_list{macro} )
	{
	    FetchMacroContent($remote_list{macro}, $options);
	}
    }
}


sub RemoteSelect {
    
    my ($pbdb_content, $macro_content);

    foreach my $piece ( @_ )
    {
	$pbdb_content = 1 if $PBDB_PIECE{$piece} && $COMMAND ne 'macrostrat';
	$macro_content = 1 if $MACRO_PIECE{$piece} && $COMMAND ne 'pbdb';
    }

    return ($pbdb_content, $macro_content);
}


sub ChooseContentPieces {
    
    my ($load_mode, $pbdb_remote, $macro_remote, $options) = @_;
    
    my @choice_list = $COMMAND eq 'macrostrat' ? @MACRO_PIECE : @PBDB_PIECE;
    my $load_source;
    
    if ( $load_mode eq 'remote' )
    {
	$load_source = "$pbdb_remote and/or $macro_remote";
    }
    
    else
    {
	$load_source = 'a local file';
    }
    
    print "\nSelect content to load from $load_source:\n\n";
    
    my $choice = AskChoice("Which piece do you wish to load?", { return_choice => 1 },
			   @choice_list);
    
    if ( $COMMAND eq 'macrostrat' && $MACRO_COMPOSITE{$choice} )
    {
	return split(/\s+/, $MACRO_COMPOSITE{$choice});
    }

    elsif ( $PBDB_COMPOSITE{$choice} )
    {
	return split(/\s+/, $PBDB_COMPOSITE{$choice});
    }
    
    else
    {
	return $choice;
    }
}


sub LoadContentFromFiles {

    my ($filename, $piece_list, $options) = @_;
    
}


sub FetchPaleobiodbContent {

    my ($piece_list, $options) = @_;
    
    # First figure out where we are fetching our content from. If the configuration setting
    # 'pbdb_master_login' is not empty, then we will fetch from the master host. Otherwise, we
    # fetch from the public host.
    
    my ($remote_host, $proxy_host, $remote_url, $backup_dir, $image_dir, $archive_dir, $datalog_dir);
    
    if ( $CONFIG{pbdb_master_login} )
    {
	unless ( $CONFIG{pbdb_master_host} )
	{
	    print "ERROR: you must specify the remote hostname in the configuration setting 'pbdb_master_host'.\n\n";
	    return;
	}
	
	$remote_host = $CONFIG{pbdb_master_login} . '@' . $CONFIG{pbdb_master_host};
	$proxy_host = $CONFIG{pbdb_proxy_host};
	$backup_dir = $CONFIG{pbdb_master_backup_dir};
	$image_dir = $CONFIG{pbdb_master_image_dir};
	$archive_dir = $CONFIG{pbdb_master_image_dir};
	$datalog_dir = $CONFIG{pbdb_master_image_dir};
    }
    
    elsif ( $CONFIG{pbdb_public_url} )
    {
	$remote_url = $CONFIG{pbdb_public_url};
	$backup_dir = $CONFIG{pbdb_public_backup_dir};
	$image_dir = $CONFIG{pbdb_public_image_dir};
	$archive_dir = $CONFIG{pbdb_public_image_dir};
	$datalog_dir = $CONFIG{pbdb_public_image_dir};
    }

    else
    {
	print "ERROR: you must specify the remote hostname or URL in the main configuration file.\n";
	print "You must specify either 'pbdb_master_login' and 'pbdb_master_host' or else 'pbdb_public_url'.\n";
	return;
    }
    
    # Check to see if we still have a recently fetched version of any of the files.
    
    my (%local_path, @fetch_list);
    
    foreach my $piece ( @$piece_list )
    {
	die "ERROR: bad key '$piece'\n" unless $LOCAL_NAME{$piece};
	my $local = "/var/tmp/" . $LOCAL_NAME{$piece};

	# If we have one, and the --auto option was not specified, ask whether to use it.
	
	if ( -r $local && ! $options->{auto} )
	{
	    my @stats = stat $local;
	    my $moddate = localtime($stats[9]);
	    
	    my $use_cached = AskQuestion("Use cached data from $local ($moddate)?",
				         { yesnoquit => 1, default => 'yes' });
	    
	    exit if $use_cached eq 'quit';
	    $local_path{$piece} = $local if $use_cached eq 'yes';
	}
	
	push @fetch_list, $piece unless $local_path{$piece};
    }
    
    # If there is at least one piece to fetch that wasn't available locally, we must make an ssh
    # connection to the remote host.
    
    if ( @fetch_list && $remote_host )
    {
	my $control_path = "/var/tmp/pbdb-remote-fetch-$remote_host";
	
	if ( MakeRemoteConnection($remote_host, $proxy_host, $control_path) )
	{
	  PIECE:
	    foreach my $piece ( @fetch_list )
	    {
		my (@remote_names, $test_pattern, $fetch_cmd, $local_file);
		
		if ( $piece eq 'images' )
		{
		    my $image_dir = $CONFIG{pbdb_master_image_dir};
		    push @remote_names, "$image_dir/*.png";
		    $test_pattern = qr{[.]png};
		    $fetch_cmd = "tar -cf - -C $image_dir . | gzip";
		    $local_file = "/var/tmp/" . $LOCAL_NAME{$piece};
		}
		
		elsif ( $piece eq 'archives' )
		{
		    my $archive_dir = $CONFIG{pbdb_master_archive_dir};
		    push @remote_names, "$archive_dir/*.header";
		    $test_pattern = qr{[.]header};
		    $fetch_cmd = "tar -cf - -C $archive_dir . | gzip";
		    $local_file = "/var/tmp/" . $LOCAL_NAME{$piece};
		}
		
		elsif ( $piece eq 'datalogs' )
		{
		    my $datalog_dir = $CONFIG{pbdb_master_datalog_dir};
		    push @remote_names, "$datalog_dir/datalog-*";
		    $test_pattern = qr{datalog-};
		    $fetch_cmd = "tar -cf - -C $datalog_dir . | gzip";
		    $local_file = "/var/tmp/" . $LOCAL_NAME{$piece};
		}
		
		elsif ( $REMOTE_NAMES{$piece} )
		{
		    my $backup_dir = $CONFIG{pbdb_master_backup_dir};
		    push @remote_names, map { "$backup_dir/$_" } @{$REMOTE_NAMES{$piece}};
		    $local_file = "/var/tmp/" . $LOCAL_NAME{$piece};
		}
		
		else
		{
		    print "ERROR: no remote filename for piece '$piece'.\n";
		    next;
		}

		# Now make sure we actually have the right path for the remote files. Test each
		# entry in @remote_names until we find one that works or have tried them all.
		
		my ($found_name, $result);
		
		foreach my $test_name ( @remote_names )
		{
		    print "  checking for $test_name...\n";
		    
		    my $result;
		    
		    # Use the ls command to look for the files on the remote system, but send
		    # stderr to /dev/null so no error message gets printed out.
		    
		    $result = CaptureCommand('ssh', '-o', "ControlPath=$control_path", $remote_host,
					     "ls $test_name 2>/dev/null");
		    
		    # else
		    # {
		    # 	$result = CaptureCommand('ssh', '-o', "ControlPath=$control_path", $remote_host,
		    # 				 "test -r $test_name && echo '$test_name'");
		    # }
		    
		    if ( $result && $test_pattern && $result =~ $test_pattern )
		    {
			print "  found $test_name\n";
			$found_name = $test_name;
			last;
		    }
		    
		    elsif ( $result && $result =~ /$test_name/ )
		    {
			print "  found $test_name\n";
			$found_name = $test_name;
			last;
		    }
		    
		    elsif ( my $rc = ResultCode() )
		    {
			print "ERROR: ssh failed with result code $rc\n" unless $rc == 1;
		    }
		}
		
		# If our remote execution of ls produced output that matched the expected name or
		# name pattern, then actually fetch the file.
		
		if ( $found_name )
		{
		    # If the piece to be fetched has an associated command (generally tar) then
		    # run it on the remote server and save the output locally.
		    
		    if ( $fetch_cmd )
		    {
			$result = SystemCommand("ssh -o ControlPath=$control_path $remote_host \"$fetch_cmd\" > $local_file");
		    }

		    # Otherwise, use scp to transfer the file to the local machine.
		    
		    else
		    {
			$result = SystemCommand('scp', '-o', "ControlPath=$control_path",
						"$remote_host:$found_name", $local_file);
		    }
		    
		    # If the command did not return an error code and the local file exists, then
		    # use it.
		    
		    if ( $result && -e $local_file )
		    {
			$local_path{$piece} = $local_file;
		    }

		    # If the command did return an error code, or if the local file is not
		    # found, complain and move on to the next piece to be fetched.
		    
		    elsif ( my $rc = ResultCode() )
		    {
			print "ERROR: ssh failed with result code $rc\n";
			next PIECE;
		    }
		    
		    else
		    {
			print "ERROR: could not fetch '$piece'.\n";
			next PIECE;
		    }
		}
		
		else
		{
		    print "ERROR: could not find '$piece' on remote host $remote_host.\n";
		    next PIECE;
		}
	    }
	    
	    print "\nClosing connection to $remote_host.\n";
	    
	    SystemCommand('ssh', '-o', "ControlPath=$control_path", '-O', 'exit', $remote_host);
	}

	else
	{
	    print "ERROR: could not make connection to $remote_host.\n";
	    return;
	}
    }

    # If we don't have anything either fetched or cached, we are done.
    
    unless ( keys %local_path )
    {
	print "\nNothing to load.\n\n";
	return;
    }
    
    # Otherwise, we proceed to load all of the pieces we were able to either fetch or cache
    # locally.
    
    my $disp = AskQuestion("Keep a copy of the fetched data in /var/tmp after loading? [y/n]",
		           { yesno => 1 });
    
    my $options = $disp eq 'no' ? { move => 1 } : { };
    
    foreach my $piece ( @$piece_list )
    {
	next unless $local_path{$piece};
	
	my $loadit = AskQuestion("Load $piece data into the Paleobiology Database from $local_path{$piece}?",
			         { yesnoquit => 1, default => 'yes' });

	return if $loadit eq 'quit';

	if ( $loadit eq 'yes' )
	{
	    print "\n";
	    
	    LoadDatabase($piece, $local_path{$piece}, $options);
	    
	    print "\n";
	}
    }    
}


sub MakeRemoteConnection {

    my ($remote_host, $proxy_host, $control_path) = @_;
    
    print "\nMaking a connection to $remote_host\n\n";
    
    my @ssh_opts = ("-o", "ControlMaster=auto", "-o", "ControlPath=$control_path", "-o", "ControlPersist=3600");
    
    if ( $proxy_host )
    {
	push @ssh_opts, "-o", "ProxyJump=$proxy_host";
    }
    
    my $check_dir = CaptureCommand('ssh', @ssh_opts, $remote_host, 'pwd');
    
    if ( my $rc = ResultCode() )
    {
	print "ERROR: ssh failed with result code $rc\n";
    }
    
    return $check_dir && $check_dir =~ qr{/};
}


sub LoadDatabase {
    
    my ($dbname, $filename, $options) = @_;
    
    $options ||= { };
    
    # The database pieces 'images', 'archives', and 'datalogs' are all directories into which
    # individual files are loaded.
    
    if ( $dbname eq 'images' || $dbname eq 'archives' || $dbname eq 'datalogs' )
    {
	# First make sure that the corresponding directory exists.
	
	unless ( -w "$MAIN_PATH/$dbname" )
	{
	    make_path("$MAIN_PATH/$dbname", { mode => 0775, verbose => 1}) ||
		SystemCommand('sudo', 'chmod', '0775', "$MAIN_PATH/$dbname") ||
		die "ERROR: could not create directory $MAIN_PATH/$dbname: $!\n";
	}
	
	# If the local filename is itself a directory, its contents will be moved or copied.
	
	if ( -d $filename )
	{
	    SystemCommand("sudo", "sh", "-c", "chmod og+r $filename/*") ||
		die "ERROR: could not chmod $filename/*\n";
	    
	    my $username = CaptureCommand("whoami");
	    chomp $username;
	    
	    if ( $username )
	    {
		SystemCommand("sudo", "sh", "-c", "chown $username $filename/*") ||
		    die "ERROR: could not chown $filename/*\n";
	    }
	    
	    if ( $options->{move} )
	    {
		print "Moving $filename/* to $MAIN_PATH/$dbname...\n";
		
		SystemCommand("sh", "-c", "mv $filename/* $MAIN_PATH/$dbname") ||
		    die "ERROR: could not mv $filename/* to $MAIN_PATH/$dbname\n";
		SystemCommand("sudo", "rmdir", $filename) ||
		    die "ERROR: could not remove directory $filename\n";
	    }
	    
	    else
	    {
		print "Copying $filename/* to $MAIN_PATH/$dbname...\n";
		
		SystemCommand("sh", "-c", "cp $filename/* $MAIN_PATH/$dbname") ||
		    die "ERROR: could not copy $filename/* into $MAIN_PATH/$dbname\n";
	    }
	}

	# Otherwise, the local filename must be a tar or tgz file.

	else
	{
	    my $zipped = $filename =~ /[.]gz$/;

	    my $unzip_cmd = $CONFIG{unzip_cmd} || 'gunzip -c';
	    
	    SystemCommand("sudo", "sh", "-c", "chmod og+r $filename") ||
		die "ERROR: could not chmod $filename\n";
	    
	    my $result;
	    
	    if ( $zipped )
	    {
		print "Unpacking $filename to $MAIN_PATH/$dbname using $unzip_cmd and tar...\n";
		print "    cd $MAIN_PATH/$dbname; $unzip_cmd $filename | tar -xvf -\n";
		
		$result = SystemCommand("cd $MAIN_PATH/$dbname; $unzip_cmd $filename | tar -xvf -");
	    }
	    
	    else
	    {
		print "Unpacking $filename to $MAIN_PATH/$dbname using tar...\n";
		print "    cd $MAIN_PATH/$dbname; tar -xvf $filename\n";
		
		$result = SystemCommand("cd $MAIN_PATH/$dbname; tar -xvf $filename");
	    }
	    
	    if ( $result )
	    {
		unlink $filename if $options->{move};
	    }

	    else
	    {
		print "ERROR: could not unpack $filename\n";
	    }
	}
	
	return;
    }

    # The individual pieces 'pbdb', 'pbdb_wing', and 'macrostrat' are all databases managed by
    # mariadb. We load the content by piping it to 'docker exec mysql'.
    
    elsif ( $dbname eq 'pbdb' || $dbname eq 'pbdb_wing' || $dbname eq 'macrostrat' )
    {
	my $zipped = $filename =~ /[.]gz$/;
	
	SystemCommand("sudo", "sh", "-c", "chmod og+r $filename") ||
	    die "ERROR: could not chmod $filename\n";
	
	my $container = $CONFIG{database_container} || 'mariadb';
	my $pbdb_load_sessions = 'no';
	my $pbdb_load_permissions = 'no';
	
	print STDOUT "\nLoading $filename into database '$dbname'...\n";
	
	if ( $dbname eq 'pbdb' )
	{
	    $pbdb_load_sessions = AskQuestion("Overwrite PBDB login session data from this file?",
					      { yesno => 1, default => "no" });
	    
	    $pbdb_load_permissions = AskQuestion("Overwrite PBDB table permission data from this file?",
					         { yesno => 1, default => "no" });
	    
	    unless ( $pbdb_load_sessions eq 'yes' )
	    {
		my $table = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'session_data'");
		
		if ( $table =~ /session_data/ )
		{
		    print "\nPreserving existing PBDB session records.\n";
		    ExecutiveCommand('pbdb', "RENAME TABLE session_data TO session_backup");
		}
	    }
	    
	    unless ( $pbdb_load_permissions eq 'yes' )
	    {	    
		my $table = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'table_permissions'");
		
		if ( $table =~ /table_permissions/ )
		{
		    print "\nPreserving existing PBDB table permissions.\n";
		    ExecutiveCommand('pbdb', "RENAME TABLE table_permissions TO permissions_backup");
		}
	    }
	}
	
	# print STDOUT "\n# You will be asked for the database ROOT password #\n\n";
	
	print "\nLoading data into '$dbname' from $filename...\n";
	
	my $unzip_cmd = $CONFIG{unzip_cmd} || 'gunzip -c';
	
	my $exun = $CONFIG{exec_username};
	my $expw = $CONFIG{exec_password};
	
	my $success;
	
	if ( $filename =~ /[.]gz$/ )
	{
	    $success = SystemCommand("$unzip_cmd $filename | docker exec -i paleobiodb_mariadb_1 " .
				     "mysql --user=$exun --password=$expw -A $dbname");
			  # 'exec', $container, 'sh', '-c',
			  # 	"zcat $INSIDE_PATH/init/$f | mysql -A -p $dbname") ||
			  # 	    die("ERROR: could not load $f into $dbname\n");
	}
	
	else
	{
	    $success = SystemCommand("cat $filename | docker exec -i paleobiodb_mariadb_1 " .
				     "mysql --user=$exun --password=$expw -A $dbname");
	    
	    # SystemDockerCompose('exec', $container, 'sh', '-c',
	    # 		    "mysql -A -p $dbname < $INSIDE_PATH/init/$f") ||
	    # 			die("ERROR: could not load $f into $dbname\n");
	}
	
	if ( $dbname eq 'pbdb' )
	{
	    unless ( $pbdb_load_sessions eq 'yes' )
	    {
		my $table = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'session_backup'");
		
		if ( $table =~ /session_backup/ )
		{
		    print "\nRestoring saved PBDB login session data.\n";
		    ExecutiveCommand($dbname, "DROP TABLE IF EXISTS session_data");
		    ExecutiveCommand($dbname, "RENAME TABLE session_backup TO session_data");
		}
		
		elsif ( $success )
		{
		    print "\nClearing PBDB login session records.\n";
		    ExecutiveCommand($dbname, "DELETE FROM session_data");
		}
	    }
	    
	    unless ( $pbdb_load_permissions eq 'yes' )
	    {
		my $table = ExecutiveQuery('pbdb', "SHOW TABLES LIKE 'permissions_backup'");
		
		if ( $table =~ /permissions_backup/ )
		{
		    print "\nRestoring saved PBDB table permission data.\n";
		    ExecutiveCommand($dbname, "DROP TABLE IF EXISTS table_permissions");
		    ExecutiveCommand($dbname, "RENAME TABLE permissions_backup TO table_permissions");
		}
		
		elsif ( $success )
		{
		    print "\nClearing PBDB table permission data.\n";
		    ExecutiveCommand($dbname, "DELETE FROM table_permissions");
		}
	    }
	}

	if ( $success )
	{
	    unlink $filename if $options->{move};
	}
	
	else
	{
	    my $rc = ResultCode();
	    print "ERROR: could not load $filename, load command returned result code $rc\n";
	    return;
	}
	
	print "\n";
	
	# Once the data is loaded, we call a subroutine that will bring the database schema up to the
	# currently expected version if it is not already there.
	
	require "PMCmd/DBVersion.pm";
	
	PMCmd::DBVersion::UpdateDatabaseSchema($dbname);
	
	print STDOUT "\nDone.\n";
    }

    else
    {
	print "ERROR: unrecognized database name '$dbname'\n";
    }
}


# Step 8 [tasks] - configure database maintenance tasks

sub TaskStep {

    # This still needs written.
}


sub ShowTasksCmd {

    # This still needs written.
}


# Step 9 [website] - choose the website configuration from the options specified above in the
# project configuration.

sub WebsiteStep {

    my ($options) = @_;
    
    # my $data_file = $CONFIG{project_data} || 'project/project-data.yml';
    
    # my $project_data = ReadConfigFile($data_file) ||
    # 	die "ERROR: the file $data_file must contain information about the project components.\n";
    
    # $project_data = $COMPONENT || die "could not find key 'component' in $data_file\n";
    
    print <<EndIntro;

Choose website configuration:
-----------------------------
EndIntro
    
    my @site_config;
    
    # Ask which of the official sites indicated above should be included in the webserver
    # configuration.
    
    my %updates;
    
    # If letsencrypt is installed on this machine but we don't already know about it, figure out
    # where it is.
    
    unless ( $CONFIG{letsencrypt_path} )
    {
    	if ( -e "/etc/letsencrypt" )
	{
	    $updates{letsencrypt_path} = "/etc/letsencrypt";
	    $CONFIG{letsencrypt_path} = $updates{letsencrypt_path};
	    print "\nFound Let's Encrypt directory at /etc/letsencrypt\n";
	}
	
	elsif ( -e "/opt/local/etc/letsencrypt" )
	{
	    $updates{letsencrypt_path} = "/opt/local/etc/letsencrypt";
	    $CONFIG{letsencrypt_path} = $updates{letsencrypt_path};
	    print "\nFound Let's Encrypt directory at /opt/local/etc/letsencrypt\n";
	}
    }
    
    # Go through all of the installed site components. For each one that has an official site
    # selected, ask if the corresponding domain should be included in the website configuration.
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	my $site_choice = $CONFIG{"site_$component"};
	
	# If this component has not been configured to be one of the official sites, then skip it.
	
	next unless $site_choice;
	
	# Otherwise, figure out what domain to serve it under. If something is misconfigured and
	# we cannot figure out a domain, complain and then skip it.
	
	my $domain = $COMPONENT{$component}{website}{$site_choice};
	my $label = $COMPONENT{$component}{label};
	
	unless ( $domain )
	{
	    print "\nERROR: no domain is established for $component '$site_choice'.\n";
	    next;
	}
	
	# Ask whether to include this domain in the website configuration.
	
	my $default = $CONFIG{"website_$component"} || 'yes';
	
	my $serve_this = AskQuestion("Serve $label on $domain?", { default => $default, yesnoquit => 1 });
	
	return if $serve_this eq 'quit';
	
	$updates{"website_$component"} = $serve_this;
	
	next unless $serve_this eq 'yes';
	
	# If so, look for a corresponding TLS certificate.
	
	my ($certfile, $keyfile ) = ChooseCertificate($domain, \%updates);
	
	return if $certfile eq 'quit';
	
	# Add a configuration section according to whether or not a certificate was found.
	
	push @site_config, SiteSection($domain, $component, $certfile, $keyfile);
    }
    
    # Now discover the local hostname. If it ends in .lan, or if it corresponds to a private IP
    # address, just use localhost.
    
    my $local_hostname;
    
    my $dflt_hostname = CaptureCommand("hostname -f");
    chomp $dflt_hostname;
    
    my $dflt_addr = CaptureCommand("host $dflt_hostname");
    
    if ( $dflt_hostname && $dflt_hostname =~ /[.]/ && $dflt_hostname !~ /[.]lan$/ &&
	 $dflt_addr && $dflt_addr !~ /10[.]\d+[.]\d+[.]\d+|192[.]168[.]\d+[.]\d+/ )
    {
	$local_hostname = $dflt_hostname;
    }
    
    else
    {
	$local_hostname = 'localhost';
    }
    
    # Ask the user which website to serve on the local hostname. This could be any of the
    # installed components, but they have to pick one.
    
    my @ask_list;
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	if ( $COMPONENT{$component}{website} )
	{
	    push @ask_list, $component, $COMPONENT{$component}{label};
	}
    }
    
    push @ask_list, 'test', 'Test webpage', 'none', 'None';
    
    my $local_site = AskChoice("Which content should be served on $local_hostname?",
			       { default => $CONFIG{website_hostname},
				 number_choices => 1, return_choice => 1 },
			       @ask_list );
    
    $updates{website_hostname} = $local_site;
    
    if ( $local_site ne 'none' )
    {
	# If we are serving the local site as 'localhost', we add an http configuration section.
	
	if ( $local_hostname eq 'localhost' )
	{
	    push @site_config, 'http-site', { domain => 'localhost',
					      config => $local_site };
	}
	
	# Otherwise, we look for a TLS certificate. If we find one, then we add an https
	# configuration section. Otherwise, the user is given the option of adding an http
	# configuration section.
	
	else
	{
	    my ($certfile, $keyfile ) = ChooseCertificate($local_hostname, \%updates);
	    
	    return if $certfile eq 'quit';
	    
	    # Add a configuration section according to whether or not a certificate was found.
	    
	    push @site_config, SiteSection($local_hostname, $local_site, $certfile, $keyfile);
	}
    }

    # Ask if there is another domain we wish the webserver to respond to.
    
    print "\nIf there is another domain that the webserver should respond to, enter it now.\n";
    print "To cancel an existing default, enter 'none'.\n";
    
    my $other_domain = AskQuestion("Other domain:", { default => $CONFIG{other_domain},
						      optional => 1 });
    
    $other_domain = '' if $other_domain eq 'none';
    
    $updates{other_domain} = $other_domain;
    
    if ( $other_domain )
    {
	my $other_site = AskChoice("Which site should be served on $other_domain?",
			           { default => $CONFIG{website_other},
				     number_choices => 1, return_choice => 1 },
				   @ask_list);
	
	$updates{website_other} = $other_site;
	
	if ( $other_site ne 'none' )
	{
	    my ($certfile, $keyfile ) = ChooseCertificate($other_domain, \%updates);
	    
	    return if $certfile eq 'quit';
	    
	    # Add a configuration section according to whether or not a certificate was found.
	    
	    push @site_config, SiteSection($other_domain, $other_site, $certfile, $keyfile);
	}
    }
    
    # Finally, ask whether to serve the installed components under the .local domains.
    
    my @local_list;
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	next unless $COMPONENT{$component}{website};
	
	my $default = $CONFIG{"localsite_$component"} || 'yes';
	
	my $label = $COMPONENT{$component}{label} || $component;
	
	my $serve_this = AskQuestion("Serve $label locally on $component.local?",
				     { default => $default, yesnoquit => 1 });
	
	return if $serve_this eq 'quit';
	
	$updates{"localsite_$component"} = $serve_this;
	
	if ( $serve_this eq 'yes' )
	{
	    push @site_config, 'http-site', { domain => "$component.local",
					      config => $component };
	    push @local_list, "$component.local";
	}
    }
    
    # If we get here, then we are ready to generate the configuration files.
    
    print "\n";
    
    RewriteLocalConfig(\%updates);
    
    GenerateFileFromTemplate($CONFIG{site_config}, $CONFIG{site_template}, 'header', @site_config);
    
    my $config_header = <<EndWebsiteConfig;
# This file stores the current website configuration for this installation.
# It is automatically generated, so editing it will have no effect except
# to kep the 'show website' subcommand from working properly.

EndWebsiteConfig
    
    WriteYAML($WEBSITE_CONFIG, $config_header, \@site_config);
    
    # If local websites are enabled, then check to see if the relevant local names are in
    # /etc/hosts. Warn the user if not.
    
    if ( @local_list )
    {
	my $etchosts = CaptureCommand("cat /etc/hosts");
	my @missing;
	
	foreach my $name ( @local_list )
	{
	    push @missing, $name unless $etchosts =~ /$name/;
	}
	
	if ( @missing )
	{
	    my $missing_list = join(', ', @missing);
	    print "\n";
	    print "WARNING: the following domains are missing from /etc/hosts:\n";
	    print "    $missing_list\n";
	    print "If you wish to make use of these domains, you will need to add them to /etc/hosts.\n\n";
	}
    }
    
    print "\n";
    
    # Now build (or rebuild) the container image for the webserver. If it builds successfully, any
    # running container for the service will be stopped and destroyed. If the webserver was already
    # running, it will be restarted.
    
    my $service = $CONFIG{webserver_service};
    
    my $result = BuildImage($service, undef, "--run=restart");
    
    # If the build is successful, remote site.conf.bak.
    
    if ( $result )
    {
	unlink "$CONFIG{site_config}.bak";
    }
    
    my $a = 1;	# we can stop here when debugging
}


# ChooseCertificate ( domain )
# 
# Attempt to locate a certificate corresponding to $domain. If one cannot be found, ask if the
# user wishes to create one using letsencrypt, or if they would like to serve the domain using
# http only.

sub ChooseCertificate {
    
    my ($domain, $updates) = @_;
    
    my $check_domain = $domain =~ tr/./_/r;
    
    # If we previously chose http only for this domain, ask the user to confirm. If the user
    # confirms the 'yes', then we are done.
    
    my $http_only;
    
    if ( $CONFIG{"http_$check_domain"} eq 'yes' )
    {
	$http_only = AskQuestion("Serve $domain using http only?",
			         { default => 'yes', yesnoquit => 1 });
	
	return ('quit') if $http_only eq 'quit';
	
	$updates->{"http_$check_domain"} = $http_only if ref $updates eq 'HASH';
	
	if ( $http_only eq 'yes' )
	{
	    return ("http");
	}
    }
    
    # Check for the certificate in the project 'certs' directory. If a certificate and
    # corresponding private key are found, return the two filenames.
    
    if ( CaptureCommand("sudo ls certs/$domain/fullchain.pem 2>/dev/null") )
    {
	if ( CaptureCommand("sudo ls certs/$domain/privkey.pem") )
	{
	    my $use_cert = AskQuestion("Use certificate certs/$domain/fullchain.pm?",
			               { default => 'yes', yesnoquit => 1 });
	    
	    if ( $use_cert eq 'yes' )
	    {
		return ("ssl/$domain/fullchain.pem", "ssl/$domain/privkey.pem");
	    }
	    
	    elsif ( $use_cert eq 'quit' )
	    {
		return ('quit');
	    }
	}
	
	else
	{
	    print "\nWARNING: Found certs/$domain/fullchain.pem, but not corresponding privkey.pem\n";
	}
    }
    
    # Otherwise, if letsencrypt is installed on this system then check for a certificate in
    # /etc/letsencrypt/live. If a certificate and corresponding private key are found, return the
    # two filenames. Otherwise, ask if a new certificate should be generated using an http challenge.
    
    if ( my $letsencrypt = $CONFIG{letsencrypt_path} )
    {
	if ( CaptureCommand("sudo ls $letsencrypt/live/$domain/fullchain.pem 2>/dev/null") )
	{
	    if ( CaptureCommand("sudo ls $letsencrypt/live/$domain/privkey.pem") )
	    {
		my $use_cert = AskQuestion("Use certificate $letsencrypt/live/$domain/fullchain.pem?",
				           { default => 'yes', yesnoquit => 1 });
		
		if ( $use_cert eq 'yes' )
		{
		    return ("/etc/letsencrypt/live/$domain/fullchain.pem",
			    "/etc/letsencrypt/live/$domain/privkey.pem");
		}
		
		elsif ( $use_cert eq 'quit' )
		{
		    return ('quit');
		}
	    }
	    
	    else
	    {
		print "\nWARNING: Found $letsencrypt/live/$domain/fullchain.pem, " .
		    "but not corresponding privkey.pem\n";
	    }
	}
	
	my $cert_default = $CONFIG{"challenge_$check_domain"} || 'yes';
	
	my $new_cert = AskQuestion("Create a new certificate for $domain using letsencrypt?",
			           { default => $cert_default, yesnoquit => 1 });
	
	if ( $new_cert eq 'yes' )
	{
	    print "\nThe webserver will be set up to allow an http-01 challenge on $domain.\n";
	    print "You can then run 'sudo certbot certonly --webroot --webrootpath=certs/challenge -d $domain'\n";
	    print "to generate the new certificate.\n";
	    
	    print "\nWhen that process has completed successfully, re-run '$COMMAND update website'\n";
	    print "to reconfigure the website to serve $domain using https.\n";
	    
	    return ("challenge");
	}

	elsif ( $new_cert eq 'no' )
	{
	    $updates->{"challenge_$check_domain"} = 'no' if ref $updates eq 'HASH';
	}

	return if $new_cert eq 'quit';
    }
    
    # If we don't have a certificate at all, ask if we should serve this domain using http only.
    
    my $http_default = $CONFIG{"http_$check_domain"} || 'yes';
    
    my $http_only = AskQuestion("Serve $domain using http only?", { default => $http_default,
								    yesnoquit => 1 });

    return if $http_only eq 'quit';
    
    $updates->{"http_$check_domain"} = $http_only if ref $updates eq 'HASH';
    
    if ( $http_only eq 'yes' )
    {
	return ("http");
    }

    else
    {
	return;
    }
}


sub SiteSection {

    my ($domain, $config, $certfile, $keyfile) = @_;
    
    # If we don't have a certificate and need to get one issued, then include a configuration that
    # will allow our webserver to respond to the ACME challenge.
    
    if ( $certfile eq "challenge" )
    {
	return ('http-challenge', { domain => $domain });
    }
    
    # If we are serving the site using http only, add an http configuration section for this
    # domain.
    
    elsif ( $certfile eq "http" )
    {
	return ('http-site', { domain => $domain,
			      config => $config });
    }
    
    # If we have a certificate, include a regular https configuration section for this domain.
    
    elsif ( $certfile && $keyfile )
    {
	my $sname = $certfile =~ /letsencrypt/ ? 'letsencrypt-site' : 'https-site';
	
	my @sections = ($sname, { domain => $domain,
				  config => $config,
				  certfile => $certfile,
				  keyfile => $keyfile });
	
	# If this is a two-component domain, i.e. 'paleobiodb.org', then add a redirect from
	# www.this.domain to this.domain.
	
	if ( $domain =~ qr{ ^ \w+ [.] \w+ $ }xs )
	{
	    push @sections, 'www-redirect', { domain => $domain };
	}

	return @sections;
    }
    
    # Otherwise, we don't include a configuration section for this domain.
    
    else
    {
	print "\nThe domain $domain will not be included in the website configuration.\n";
	return;
    }
}


sub ShowWebsiteCmd {
    
    my ($options) = @_;
    
    unless ( -e $WEBSITE_CONFIG )
    {
	print "The website configuration has not yet been set up.\n";
    }
    
    my $website_config = ReadConfigFile($WEBSITE_CONFIG);
    
    unless ( ref $website_config eq 'ARRAY' && @$website_config )
    {
	print "The website configuration file could not be read.\n";
	return;
    }
    
    my (@domain, @protocol, @config, @certs);

    while ( @$website_config )
    {
	my $type = shift @$website_config;
	my $attrs = shift @$website_config;

	unless ( $type && ref $attrs eq 'HASH' )
	{
	    push @domain, 'ERROR reading file';
	    last;
	}

	my $certfile = $attrs->{certfile} || '';

	if ( $certfile )
	{
	    $certfile =~ s{^ssl}{frontend/certs};
	}
	
	push @domain, ($attrs->{domain} || '??');
	push @protocol, ($type eq 'http-site' ? 'http' : 'https');
	push @config, ($attrs->{config} || '??');
	push @certs, $certfile;
    }

    PrintOutputList($options, ['Domain', 'Protocol', 'Configuration', 'Certificate'],
		    \@domain, \@protocol, \@config, \@certs);
}


sub WriteYAML {
    
    my ($filename, $header, @data) = @_;

    require YAML::Tiny;
    
    my $yaml = YAML::Tiny->new(@data);
    
    open(my $outfh, '>', $filename);

    if ( $outfh )
    {
	print $outfh $header;
	print $outfh $yaml->write_string;
	close $outfh;
    }

    else
    {
	print "\nWARNING: could not write $filename: $!\n";
    }
}


# Step 10 [finish] - bring up all services

sub FinishStep {
    
    my ($mode) = @_;
    
    print "\nInstallation is now complete. Bringing up all services...\n";
    
    # print "Bringing up all services...\n";

    SystemDockerCompose('up', '-d');

    sleep(5);
    return DisplayStatus('all');
}


# # CheckCmd ( )
# # 
# # Check the status of one or more parts of the installation. 

# $LDOC{check} = <<EndCheck;

# Usage:  {NAME} check SUBCOMMAND [OPTIONS]

# Check one or more parts of the installation.

# Options:

#   --quiet, -q   Only print output corresponding to an unusual or error condition.

# Subcommands are:

#   repos         Print a line of output for each Git repository in the installation, indicating
#                 whether it has any uncommitted changes or is ahead of the remote registry.
#                 A repo that is on branch 'master' and has no uncommitted changes will display
#                 in green. A repo that has uncommitted changes or is ahead of its remote
#                 repository by one or more commits will display in red. A repo that is up to
#                 date but on a branch other than 'master' will display in yellow.

#                 This subcommand is identical to '{NAME} update repos --check'.
                
# EndCheck
    
# sub CheckCmd {
    
#     my $cmd = shift @ARGV;
    
#     my $step;
    
#     # Look for options either before or after the update step name.
    
#     if ( $ARGV[0] !~ /^-/ )
#     {
# 	$step = shift @ARGV;
#     }
    
#     my ($opt_quiet, $opt_nocolor);
    
#     GetOptions( 'quiet|q' => \$opt_quiet,
# 	        'nocolor' => \$opt_nocolor );
    
#     unless ( $step )
#     {
# 	$step = shift @ARGV;
#     }
    
#     die "ERROR: you must specify a subcommand\n" unless $step;
    
#     my $options = { check => $step };
#     $options->{quiet} = 1 if $opt_quiet;
#     $options->{nocolor} = 1 if $opt_nocolor;
    
#     # Read the local configuration file in preparation for executing the specified subcommand.
    
#     ReadLocalConfig;
    
#     # If there is either an update step or an install step corresponding to the argument, execute
#     # it now.
    
#     my $routine = $CHECK_STEP{$step};
    
#     if ( $routine )
#     {
# 	return &$routine( $options );
#     }
    
#     else
#     {
# 	print "ERROR: '$step' is not a check subcommand\n";
# 	print "\nAvailable update subcommands are:\n";
# 	print "    $_\n" foreach @CHECK_STEP;
# 	die "\n";
#     }
# }


# HelpString ( sub, subsub )
# 
# Return the help string for the specified subcommand. If a sub-subcommand is specified, show the
# specific documentation for it.

sub HelpString {

    my ($first, $second) = @_;
    
    # If we have more specific documentation, display that.
    
    $second = 'password' if $second eq 'api' || $second eq 'exec' || $second eq 'root';
    
    if ( $second && $SDOC{$first}{$second} )
    {
	my $doc = $SDOC{$first}{usage};
	
	my $args = $ADOC{$first}{$second} || '';
	
	$doc =~ s/{SUBCOMMAND}/$second/;
	$doc =~ s/{ARGS}/$args/;

	$doc .= $SDOC{$first}{$second};

	return $doc;
    }
    
    # Otherwise, display the less specific documentation if we have it.
    
    elsif ( $LDOC{$first} )
    {
	return $LDOC{$first};
    }
    
    else
    {
	return "\nNo documentation is available for the subcommand '$first'\n\n";
    }
}


1;
