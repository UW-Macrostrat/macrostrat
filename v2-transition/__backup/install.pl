# 
# Paleobiology/Macrostrat install script
# 
# This script installs the Paleobiology Database and/or Macrostrat in their dockerized forms. The
# first thing it does is to ask the user which of these projects to install. If both are
# installed, they share the frontend webserver (nginx) and the MariaDB server (mariadb). All other
# components are run in separate containers.
# 
# If you install only one of the projects and later wish to add the other, you must run this
# script again. If you do this, you will have the chance to preserve all database content.
# 
# Author: Michael McClennen
# Created: 2019-11-20
# Macrostrat added: 2020-05-18
# 


use 5.018001;
use strict;

# This script is intended to be run before the accompanying Perl modules are
# installed. Therefore, we must include them directly from the source directory.

use lib 'command/lib';

use PMCmd::Config qw(%CONFIG %DEFAULT $MAIN_PATH $MAIN_NAME $DEBUG $COMMAND
		     $MASTER_COMPOSE $LOCAL_COMPOSE $LOCAL_CONFIG
		     ReadLocalConfig AskQuestion);
use PMCmd::Install qw(IsInstallStep DoInstallStep StepLabel AllSteps);
use PMCmd::Build qw(ReadComponentData);

use File::Copy;
use Cwd qw(getcwd);
use Getopt::Long;


my @DEPS = qw(docker-compose make git YAML/Tiny.pm);

my %PKG = ( 'YAML/Tiny.pm' => { apt => 'sudo apt install libyaml-tiny-perl',
				port => 'sudo port install p5-yaml-tiny' },
	    'make' => { port => 'sudo xcode-select --install' } );

# First figure out where we are located.

$MAIN_PATH = getcwd();

$MAIN_PATH =~ qr{ ([^/]+) $ }xs || die "ERROR: could not determine last component of main path\n";
$MAIN_NAME = $1;

# Next check that this script is actually being run from the base directory for the project.
# Confirm that a few of the necessary files are there.

unless ( -r ".git" && -r $DEFAULT{main_setup_template} && -r $DEFAULT{main_compose_template} )
{
    print "\nERROR: you must run this script from the directory in which it is located.\n";
    print "This must be the directory into which you cloned the base repository.\n\n";
    exit;
}

# Also check that the last path component of the main directory is either 'paleobiodb',
# 'macrostrat', or 'paleomacro'. If it is none of these, inform the user that they must
# rename it to one of these components.

unless ( $MAIN_PATH =~ qr{ [/] (paleobiodb|macrostrat|paleomacro) $ }xs )
{
    print "\nThe main directory for this project must have one of the following names\n";
    print "as its final path component:\n";
    print " - paleobiodb\n";
    print " - macrostrat\n";
    print " - paleomacro\n";
    print "\nChoose one of these and rename the current directory to it, and then re-run\n";
    print "this command.\n";
    exit;
}

# Record that we are running the install script rather than the 'pbdb' or 'macrostrat' command
# scripts. This allows code in other modules to be aware of the context in which it is being run.

$COMMAND = 'install';

# Check for options.

my ($all_steps, $show_help, $opt_restart, $opt_clean, $install_bin);

GetOptions( "help|h" => \$show_help,
	    "clean|c" => \$opt_clean,
	    "restart|r" => \$opt_restart,
	    "install-bin=s" => \$install_bin,
	    "debug|d" => \$PMCmd::Config::DEBUG);

# If the user provided an argument to this command, it should be one of the step names or a number
# corresponding to one of the steps. If the argument is 'help' or if -h or --help was given as an
# option, show the help string and quit.

my $initial = shift @ARGV;

if ( $show_help || $initial eq 'help' )
{
    DoHelp();
}

elsif ( $initial || $opt_restart || $opt_clean )
{
    # To prevent needless hassle, we interpret 'contents' as if the user had typed 'content'
    # instead. So either word will have the same effect.
    
    if ( $initial eq 'contents' ) { $initial = 'content'; }
    
    # The --restart option is the same as specifying 'start' as the step name.
    
    $initial = 'start' if $opt_restart || $opt_clean;
    
    # Make sure that the specified word is actually a step in the process.
    
    die "ERROR: '$initial' is not a step in the installation process.\n"
	unless IsInstallStep($initial) || $initial eq 'start';
    
    DoInstall($initial);
}

else
{
    DoInstall();
}

# We are done when DoInstall returns, so 'bye.

exit;


# DoInstall ( initstep )
#
# Execute the installation procedure, optionally starting at the named step.

sub DoInstall {

    my ($initstep) = @_;
    
    # If no initial step was indicated but the file '.install' exists and is not empty, then read
    # that file to determine our starting step. This is the mechanism by which an interrupted
    # installation can be easily started up again after the last completed step.
    
    if ( ! $initstep && -e '.install' )
    {
	$initstep = `cat .install`;
	chomp $initstep;
    }
    
    # If the initial step was given as 'start', then just clear that variable so that no steps
    # will be skipped. If no value was given, set it to the empty string. Write the value 'start'
    # to .install, so we will start there again if the installation is interrupted during the
    # first step.
    
    if ( $initstep eq 'start' || ! defined $initstep )
    {
	$initstep = '';
	system("echo 'start' > .install");
     }

    # If the initial step is 'finish', then we just execute that step and stop.

    elsif ( $initstep eq 'finish' )
    {
	DoInstallStep('finish');
	return;
    }
    
    # If the initial step is 'postgresql' or 'mariadb', then we change it to 'database' and record that
    # 'postgresql' is the actual step to execute.
    
    my $altstep = '';
    
    if ( $initstep eq 'postgresql' || $initstep eq 'mariadb' )
    {
	$altstep = $initstep;
	$initstep = 'database';
    }
    
    # Execute initial tasks, including dependency checks. 
    
    CheckDeps(@DEPS);
    DisplayBanner();
    InitSudo();
    
    # Make sure the umask is correct.
    
    umask 0022;
    
    # Do one more check, because the docker login process is broken if docker-compose is also
    # installed. The necessary fix is simple, but we need to do it if it hasn't been already done. It
    # involves renaming docker-credential-secretservice out of the way so it won't get called. This
    # action was placed at this point in the code because it needs to be after the call to InitSudo.
    
    if ( -e "/usr/bin/docker-credential-secretservice" )
    {
	system("sudo", "mv", "/usr/bin/docker-credential-secretservice",
	       "/usr/bin/docker-credential-secretservice.broken");
    }
    
    # If the local configuration file doesn't exist, create it by making a copy of the base
    # file. If --clean was specified, copy the base file on top of it and discard all previous
    # local configuration information.
    
    unless ( -e $LOCAL_CONFIG || $opt_clean )
    {
	copy($DEFAULT{main_config_base}, $LOCAL_CONFIG) ||
	    die "ERROR: could not copy $DEFAULT{main_config_base} to $LOCAL_CONFIG: $!\n";
    }
    
    unless ( -r $LOCAL_CONFIG )
    {
	die "ERROR: could not read $LOCAL_CONFIG: $!\n";
    }
    
    # Now read the local configuration file and initialize the %CONFIG hash.
    
    ReadLocalConfig({ empty_ok => 1 });
    
    # Adjust the local configuration based on the options as given.
    
    if ( $install_bin )
    {
	$CONFIG{install_bin_new} = $install_bin;
    }
    
    # If --clean was specified, remove the rest of the main configuration files so that they will
    # be regenerated from the base files.
    
    if ( $opt_clean )
    {
	if ( -e $MASTER_COMPOSE )
	{
	    unlink $MASTER_COMPOSE || die "Could not remove $MASTER_COMPOSE: $!\n";
	}

	if ( -e $LOCAL_COMPOSE )
	{
	    unlink $LOCAL_COMPOSE || die "Could not remove $LOCAL_COMPOSE: $!\n";
	}
	
	if ( $DEFAULT{master_setup} && -e $DEFAULT{master_setup} )
	{
	    unlink $DEFAULT{master_setup} || die "Could not remove $DEFAULT{master_setup}: $!\n";
	}

	if ( $DEFAULT{local_setup} && -e $DEFAULT{local_setup} )
	{
	    unlink $DEFAULT{local_setup} || die "Could not remove $DEFAULT{local_setup}: $!\n";
	}
    }
    
    # Read the component data. If the 'project' step hasn't been executed yet, this data will be
    # incomplete. In that case, it will be filled in during the execution of that step.
    
    ReadComponentData();
    
    # Then grab the list of initialization steps. If an initial step was given, we skip steps until
    # we find it.
    
    my @steps = AllSteps;
    
    if ( $initstep && IsInstallStep($initstep) )
    {
	shift @steps while @steps && $steps[0] ne $initstep;
    }
    
    # Then execute the rest of the steps one by one.
    
 STEP:
    foreach my $i ( 0..$#steps )
    {
	my $s = $steps[$i];
	
	if ( $altstep )
	{
	    $s = $altstep; $altstep = '';
	}
	
	# We want to make absolutely certain that we are in the right directory before starting each step.
	
	chdir $MAIN_PATH;
	
	my $label = StepLabel($s);
	my $rule = '-' x length($label);
	
	print "\n";
	print "$label\n";
	print "$rule\n";
	
	# For each step except the first (command) step, ask if the user wants to execute it.
	
	my $dothis = AskQuestion("Execute this step? (y/n/q) ", { yesnoquit => 1, default => 'yes' });
	
	last STEP if $dothis eq 'quit';
	next STEP unless $dothis eq 'yes';
	
	# Call the routine for the current step.
	
	DoInstallStep($s);
	
	# # If this was the specified initial step, and --all was not specified, then ask if the
	# # user wishes to continue the installation.
	
	# if ( $initstep && ! $all_steps)
	# {
	#     my $answer = AskQuestion("Continue the installation?", 'y', { yesno => 1 });
	#     last unless $answer eq 'y';
	# }
	
	# Now that we have successfully completed a step, we write into the file .install the name
	# of the next step. This will make sure that if the installation is interrupted it will
	# start again with the step immediately following the last successfully completed step. At
	# the very end of the process, we should be left with '.finish' in .install.
	
	my $next_step = $steps[$i+1] || 'finish';
	
	system("echo '$next_step' > .install");
    }
}


sub DoHelp {

    print <<EndHelp

Usage: perl install.pl [OPTIONS] [STEP]

Install the Paleobiology Database service bundle on this machine. With no
arguments, it runs through the entire set of installation steps. If stopped and
then rerun, it starts after the last completed step. You can start at a
specified step by giving the step name as an argument.

The steps are:

  project      Asks you to choose which project components to install
  
  command      Installs or updates the 'pbdb' and 'macrostrat' commands.
  
  repos        Pulls all of the necessary repositories, and checks to make sure
               that the necessary directories and symlinks are in place.
  
  config       Asks questions, and then generates the configuration files
               for all of the component services.
  
  images       Pulls base images from a remote repository, and then builds all
               of the container images.
  
  database     Initializes the database and asks you to choose passwords.
  
  content      Loads the database content, either from a remote
               site or from files.
  
  website      Asks you to choose the webserver site configuration and brings it up.
  
  finish       Brings up all services.

Options:
  --help              Show this message and exit
  --restart           Start the installation from the beginning, even if some
                        steps have already been completed
  --clean             Start the installation from the beginning, and start with the
                        base configuration files. Wipe out any local configuration
                        changes that may have been made. Database content will be
                        preserved unless specifically erased in the 'database' step.
  --install-bin=DIR   Install the 'pbdb' command in the specified directory
  --debug, -d         Display all of the commands executed by the installation
                        procedure.

EndHelp
    
}


# CheckDeps ( )
#
# Check for the packages on which this script depends. Abort if any are not found, but attempt to
# print a reasonable message indicating what to do to install them. Check all dependencies before
# returning, so that the user has a full list of what is necessary to install.

sub CheckDeps {

    print "Checking dependencies...\n";
    
    my @deps = @_;
    my $notfound;
    
    # First check all of the dependencies.
    
    foreach my $d ( @deps )
    {
	$notfound = 1 unless CheckOneDependency($d);
    }
    
    if ( $notfound )
    {
	print "You must install the necessary packages and then re-run this script.\n\n";
	exit(2);
    }
    
    my $test = `docker ps -a`;
    
    if ( $test )
    {
	print "Good.\n\n";
    }
    
    else
    {
	print "The docker command is not functioning correctly.\nYou may need to add your userid to the 'docker' group in /etc/group.\n";
	exit(2);
    }
}


sub CheckOneDependency {
    
    my ($cmd) = @_;

    # If the dependency is a Perl module, then check if Perl can load it.
    
    if ( $cmd =~ /[.]pm$/ )
    {
	my $found = eval { require $cmd };

	if ( $found )
	{
	    return $found;
	}
	
	elsif ( `which apt-get` )
	{
	    my $c = $PKG{$cmd}{apt};
	    print "Module '$cmd' not found, but can be installed with:\n\n$c\n\n";	    
	}
	
	elsif ( -e '/opt/local' && `port -v` =~ /macports/i )
	{
	    my $c = $PKG{$cmd}{port};
	    print "Module '$cmd' not found, but can be installed with:\n\n$c\n\n";
	}
	
	else
	{
	    my $module = $cmd;
	    $module =~ s{/}{::}g;
	    $module =~ s/[.]pm$//;
	    print "Module '$module' not found, but can be installed with:\n\nsudo cpan $module\n\n";
	}
    }
    
    # Otherwise, assume it is a command and look for it in the current path.

    else
    {
	if ( my $cmd_path = `which $cmd` )
	{
	    return $cmd_path;
	}
	
	# If not found, figure out the ways in which it could be installed.
	
	elsif ( `which apt-get` )
	{
	    my $c = $PKG{$cmd}{apt} || "sudo apt install $cmd";
	    print "\Command '$cmd' not found, but can be installed with:\n\n$c\n\n";
	}
	
	elsif ( -e '/opt/local' && `port -v` =~ /macports/i )
	{
	    my $c = $PKG{$cmd}{port} || "sudo port install $cmd";
	    print "\Command '$cmd' not found, but can be installed with:\n\n$c\n\n";
	}
	
	else
	{
	    print "\Command '$cmd' not found, you must install it before continuing.\n\n";
	}
    }

    return undef;
}


# DisplayBanner ( )
#
# Display a block of text explaining the operation of this command.

sub DisplayBanner {
    
print <<ENDBanner;
This command will install and configure a dockerized instance of the Paleobiology Database
or Macrostrat or both on this machine. The installation process consists of several steps,
and if any of them fail you can restart at the specified step by running this script again
with the step name or number as an argument. The steps are:

  1) project - choose which project components to install on this machine
  2) command - install the status and control commands: 'pbdb' and 'macrostrat'
  3) repos - pull the necessary git repos into the appropriate subdirectories
  4) config - generate the necessary configuration files
  5) images - pull base images and build container images
  6) database - initialize the database and set passwords
  7) content - load the database content, from local files or a remote site
  8) website - configure the website
  9) finish - bring up all services

All of these steps can be run or re-run individually using the 'pbdb update' or
'macrostrat update' command with the step name as the first argument. Many of these
may need to be re-run regularly to incorporate ongoing changes to the codebase.

If you have not run 'sudo' within the last few minutes, you will be asked
for your password at the beginning. This will enable the script to run sudo
as needed without interrupting you for your password later.

ENDBanner

}


# InitSudo ( )
#
# Execute a test sudo command, so that if the user needs to provide their password this happens at
# the beginning instead of whenever a sudo happens to be needed during the installation
# process. If the user cancels or provides an invalid password, this script will exit.

sub InitSudo {
    
    system("sudo touch testfile");
    
    if ( -e "testfile" )
    {
	unlink("testfile");
    }
    
    else
    {
	exit;
    }
}


