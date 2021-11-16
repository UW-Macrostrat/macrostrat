#
# Paleobiology Database build command
# 
# This module implements the guts of the paleobiodb build command.
# 
# Author: Michael McClennen
# Created: 2019-12-13


use strict;

package PMCmd::Build;

use parent 'Exporter';

use PMCmd::Config qw(%CONFIG %COMPONENT $MAIN_PATH $COMMAND $DEBUG
		     @INSTALLED_COMPONENTS @DB_COMPONENTS @WS_COMPONENTS @COMPONENT_CONF
		     ReadLocalConfig ReadConfigFile AskQuestion MainName);
use PMCmd::Command qw(DisplayStatus);
use PMCmd::System qw(GetComposeServices GetServiceStatus GetComposeYAML PrintDebug
		       ExecDockerCompose SystemDockerCompose SystemCommand CaptureCommand);

use Scalar::Util qw(reftype);
use Getopt::Long;
use Cwd;

our (@EXPORT_OK) = qw(BuildImage FindImage FindBuiltImage RebuildCopyMap PushPullImages
		      ReadComponentData ListComponentTemplates ReadTemplate CheckTemplateTarget
		      GenerateFileFromTemplate GenerateYAMLFromTemplate BuildNginxDockerfile );

our (%LDOC);


# BuildCmd ( )
#
# This routine implements the subcommand 'build'.

$LDOC{build} = <<ENDBuild;

Usage:  {NAME} build [OPTIONS] [SERVICE]

        {NAME} build preload [OPTIONS] [SERVICE]

With no options, build the container image for the specified service or
else rebuild the preload image on top of which the container image is
defined. Some of the options described below provide for listing and
manipulating the available versions of these images.

The main images are all named in the pattern "project_service:tag",
where the first part is the name of the main directory in which the project
files are located and the second part is the name of the service. The
preload images are named in the pattern "project_service_preload:tag",
where 'preload' is a literal string. If the -t option is not specified,
the newly built image will be tagged as 'latest'.

If this is a preload build tagged as latest, you will be asked if you
want to check the new image by using it to build a test version of the
container image for this service. If it is a container image, regardless
of tag, the image will be inspected for the presence of a 'buildcheck'
label. If this label is found, its value will be run as a command in a
temporary container using this image and you will be asked to approve
or reject the new image on the basis of the command output. For example,
the buildcheck command specified in the nginx Dockerfile is "nginx -t".
If the command is 'sh', an interactive shell will be run and you will
have a chance to take whatever actions are necessary in order to decide
whether to approve or reject the image.

If you reject a newly built image, you will be asked to enter a tag to
save it under for later analysis or use. If you do not provide one, the
image will be deleted. In either case, the previous latest version of
the image (if there was one) will be restored to 'latest'.

If you accept a newly built container image, you will be presented with
a list of all services and other containers that are running with the
previous version of this image. For each one, you will be asked whether
to preserve it, destroy it, or in the case of a service container
recreate it with the new image.

If any of the following options are specified, no build will be done.
For each of these options, the service name 'all' is accepted.

  --list             List all available image versions for the specified
                       service, or for all services.
  --select=tag       Tag the image version with the specified tag as 'latest'.
                       this will remove the image previously tagged as
                       latest if it did not have any other tags.           
  --cleanup=tag      Remove the image version with the specified tag. If no tag
                       is given, removes 'good', 'previous', and 'test'.

Otherwise, a build will be done. Build options include:

  -t,--tag=tag       Give the new image the specified tag, rather than
                       tagging it as latest.
  --test             Give the new image the tag 'test'.
  --save=tag         Tag the current latest version of the image with the
                       specified tag before the build is done, so that it
                       will not be deleted and can be restored later if
                       necessary. If just --save is given, defaults to 'good'.
  --no-check         Skip the build check, and approve any image that builds
                       successfully.
  --run              If the new image is accepted, destroy or recreate all
                       running containers that used the old image. Without
                       this option, you will be asked about each one.

Any unrecognized options will be passed unchanged to docker build. The
options --build-arg and --label can be followed by a key=value list
as a subsequent argument, but all other build options should use the
single-argument form --option=value.

ENDBuild

sub BuildCmd {

    # The command to be executed will be at the beginning of @ARGV.
    
    my $cmd = shift @ARGV;

    # Read the configuration file for this project.

    ReadLocalConfig();
    
    # Check for the subcommand 'preload'. If present, it must be the very first argument.
    
    my ($opt_preload, $opt_nocheck, $opt_run, $opt_timezone, $opt_build_tag);
    my ($opt_save_tag, $opt_select_tag, $opt_remove_tag, $opt_list_tags);
    
    # The options -t, --tag, --test, and --no-check are recognized. Any remaining options will be
    # passed along to 'docker build'. The option --build-arg is assumed to take a separate
    # argument afterward, but all other arguments with values should be specified on the command
    # line as --option=value. Otherwise, this command will fail.

    my @services;
    my @build_options;
    
    while ( @ARGV )
    {
	if ( $ARGV[0] eq '-t' || $ARGV[0] eq '--tag' )
	{
	    shift @ARGV;
	    $opt_build_tag = shift @ARGV;
	    next;
	}
	
	if ( $ARGV[0] =~ qr{ ^ --(tag|save|select|cleanup|run)= (.*) | 
			     ^ --(t|tag|test|save|select|cleanup|list|run) $ }xs )
	{
	    if ( $3 eq 'list' )
	    {
		$opt_list_tags = 1;
	    }
	    
	    elsif ( $1 eq 'select' || $3 eq 'select' )
	    {
		$opt_select_tag = $2 || 'nothing';
		$opt_list_tags = 1;
	    }
	    
	    elsif ( $1 eq 'cleanup' || $3 eq 'cleanup' )
	    {
		$opt_remove_tag = $2 || 'default';
		$opt_list_tags = 1;
	    }
	    
	    elsif ( $1 eq 'tag' || $3 eq 'test' )
	    {
		$opt_build_tag = $2 || 'test';
	    }
	    
	    elsif ( $1 eq 'save' || $3 eq 'save' )
	    {
		$opt_save_tag = $2 || 'good';
	    }
	    
	    elsif ( $1 eq 'run' || $3 eq 'run' )
	    {
		$opt_run = $2 || 'yes';

		unless ( $opt_run =~ / ^ (?: yes|restart|no|check|nocheck) $ /xs )
		{
		    die "Invalid run option '$opt_run'.\n";
		}
	    }
	    
	    else
	    {
		die "ERROR: unrecognized option '$ARGV[0]'\n";
	    }
	    
	    shift @ARGV;
	    next;
	}
	
	elsif ( $ARGV[0] =~ qr{ ^ --(timezone) (?: = (.*))? }xs )
	{
	    $opt_timezone = $2;
	}
	
	elsif ( $ARGV[0] =~ qr{ ^ (--)? preload $ }xs )
	{
	    $opt_preload = 1;
	    shift @ARGV;
	    next;
	}

	elsif ( $ARGV[0] !~ /^-/ )
	{
	    push @services, shift @ARGV;
	    next;
	}
	
	if ( $ARGV[0] eq '--build-arg' || $ARGV[0] eq '--label' )
	{
	    push @build_options, shift @ARGV;
	}
	
	push @build_options, shift @ARGV;
    }
    
    # Make sure we are building a single service. If the service name is 'api', then build the
    # correct service according to which command is being run.
    
    die "ERROR: You must specify at least one service to build.\n" unless @services;
    die "ERROR: You may not specify more than one service: '$services[0]', '$services[1]', ...\n" if @services > 1;
    
    my $build_service = shift @services;
    
    if ( $build_service eq 'api' )
    {
	$build_service = 'pbapi' if $COMMAND eq 'pbdb';
	$build_service = 'msapi' if $COMMAND eq 'macrostrat';
    }
    
    my %services = map { $_ => 1 } GetComposeServices();
    
    unless ( $services{$build_service} || $build_service eq 'all' && $opt_list_tags)
    {
	die "ERROR: '$build_service' is not a $COMMAND service.\n";
    }
    
    # Determine the name for the image to be built, based on the service name.
    
    my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
    my $image_name;
    
    if ( $opt_preload )
    {
	$image_name = join('_', 'paleomacro', $build_service, 'preload');
    }

    else
    {
	$image_name = join('_', $base_name, $build_service);
    }
    
    # Start by checking for tag options.
    
    # If the option --select was given, retag the specified image to 'latest' and return.
    
    if ( $opt_select_tag )
    {
	die "You may not specify --select and --cleanup together.\n" if $opt_remove_tag;
	die "Invalid argument 'latest'.\n" if $opt_select_tag eq 'latest';
	
	if ( $opt_select_tag eq 'nothing' )
	{
	    die "You must specify a value with the --select option.\n";
	}
	
	elsif ( ! FindImage("$image_name:$opt_select_tag") )
	{
	    print "Image $image_name:$opt_select_tag was not found.\n";
	    return;
	}
	
	# If we have identified a valid image tag, so tag it also as 'latest'.
	
	if ( $opt_select_tag )
	{
	    my $tag_id = GetImageID("$image_name:$opt_select_tag");
	    my $latest_id = GetImageID("$image_name:latest");
	    
	    # If this tag already refers to the same image as latest, nothing needs to change.
	    
	    if ( $tag_id && $latest_id && $tag_id eq $latest_id )
	    {
		print "Image $image_name:$opt_select_tag is the same as $image_name:latest.\n";
		return;
	    }
	    
	    unless ( $opt_preload )
	    {
		my $result = StopRunningContainers("$image_name:latest", 'ask');
		return unless $result;
	    }
	    
	    print "Tagging $image_name:$opt_select_tag => latest\n";
	    SystemCommand('docker', 'tag', "$image_name:$opt_select_tag", "$image_name:latest");
	    SystemCommand('docker', 'image', 'ls', $image_name);
	}
	
	return;
    }
    
    # If the option --cleanup was given, remove the specified tag(s) now and return.
    
    if ( $opt_remove_tag )
    {
	my @remove_tag = $opt_remove_tag;
	my $remove_count;
	
	die "You may not specify --select and --cleanup together.\n" if $opt_select_tag;
	die "Invalid argument 'latest'.\n" if $opt_remove_tag eq 'latest';
	
	if ( $opt_remove_tag eq 'default' )
	{
	    @remove_tag = ('good', 'previous', 'test');
	}
	
	my @remove_image;
	
	if ( $build_service eq 'all' )
	{
	    foreach my $s ( keys %services )
	    {
		my $iname = join('_', $base_name, $s);
		$iname .= '_preload' if $opt_preload;
		push @remove_image, $iname;
	    }
	    
	    $image_name = $base_name . '_*';
	}

	else
	{
	    @remove_image = $image_name;
	}
	
	foreach my $iname ( @remove_image )
	{
	    my $latest_id = GetImageID("$iname:latest");
	    
	    foreach my $tag ( @remove_tag )
	    {	
		my $cleanup_id = GetImageID("$iname:$tag");
		next unless $cleanup_id;
		
		# If this tag is different from the latest version, check for
		# running containers before removing.
		
		if ( $latest_id && $latest_id ne $cleanup_id )
		{
		    StopRunningContainers("$iname:$tag", 'ask') || next;
		}
		
		SystemCommand('docker', 'rmi', "$iname:$tag");
		$remove_count++;
	    }
	}

	print "Nothing removed.\n" unless $remove_count;
    }

    if ( $opt_list_tags )
    {
	SystemCommand('docker', 'image', 'ls', $image_name);
	return;
    }
    
    # If the option --save was given, then add an extra tag to the current
    # latest image. Then keep going to the build.
    
    if ( $opt_save_tag )
    {
	print "\nSaving current image as $image_name:$opt_save_tag\n\n";
	SystemCommand('docker', 'tag', "$image_name:latest", "$image_name:$opt_save_tag");
    }
    
    # If the option --tag or -t was given, add the specified name to the image.
    
    $image_name = "$image_name:$opt_build_tag" if $opt_build_tag;

    # If the option --timezone was given, add it to the front of the option list. The value may be
    # the empty string.
    
    unshift @build_options, "--timezone=$opt_timezone" if defined $opt_timezone;
    
    # If the option --run was given, just add it on the front of the option list.
    # It will be removed by BuildImage.
    
    unshift @build_options, "--run=$opt_run" if $opt_run;
    
    # Now either build the service image or else the preload image from which the service image
    # will get built.
    
    BuildImage($build_service, $image_name, \@build_options);
}


# FindImage ( image_name )
#
# Return the image name if it exists, or the empty string if not. If there are no underscores in
# the name, assume it is a service name and build an image name from that.

sub FindImage {

    my ($image_name) = @_;
    
    return '' unless $image_name;
    
    unless ( $image_name =~ /_/ )
    {
	$image_name = MainName() . "_$image_name";
    }
    
    return CaptureCommand('docker', 'image', 'ls', '--quiet', $image_name) ? $image_name : '';
}


# FindBuildImage ( service )
# 
# Return the image name corresponding to the service if it exists and is newer than the
# corresponding preload image, or the empty string if not.

sub FindBuiltImage {

    my ($service_name) = @_;
    
    return '' unless $service_name;
    
    my $image_name = join('_', MainName(), $service_name);
    my $preload_name = join('_', 'paleomacro', $service_name, 'preload');
    
    return CaptureCommand('docker', 'image', 'ls', '--quiet',
			  '--filter', "since=$preload_name:latest", "$image_name:latest")
	? $image_name : '';
}


# GetImageID ( image_name )
#
# Return the id of the image if it exists, or the empty string if not.

sub GetImageID {

    my ($image_name) = @_;
    
    return '' unless $image_name;
    return CaptureCommand('docker', 'image', 'ls', '--quiet', $image_name);
}


# BuildImage ( service, image_name, build_opts )
#
# Build a container image for the specified service. If any build options are specified, they are
# passed along to the docker build command.
# 
# If the image name contains the string '_preload', then Dockerfile_preload is used instead of
# Dockerfile. If the build is successful, the user is then asked whether they want to test it by
# building the main container image and running the build check. If this passes, then the user
# is given the opportunity to accept or reject the new image.
# 
# Otherwise, the main image is built using the latest version of the existing preload image. If
# the build is successful, the image is checked for a 'buildcheck' label. If one exists, the value
# of this label is run as a command in a container with the new image. The user is then given the
# opportunity to accept or reject the new image. If accepted, then any running containers
# associated with the given service are listed and the user is given the option of restarting or
# destroying them.
# 
# If a build is rejected by the user, then the 'latest' tag is reassigned to the previous version of
# this image, which was kept under the 'previous' tag.

sub BuildImage {

    my ($service, $image_name, $build_opt_list) = @_;
    
    # If no image name was specified, then by default we will build the container image for the
    # specified service.
    
    unless ( $image_name )
    {
	my ($base_name) = $MAIN_PATH =~ qr{([^/]+)/?$};
	$image_name = join('_', $base_name, $service);
    }
    
    # If the third argument is a single build option rather than a list, then turn it into a list
    # if it starts with a hyphen. Otherwise, we ignore it and use an empty build option list.
    
    unless ( ref $build_opt_list eq 'ARRAY' )
    {
	if ( $build_opt_list =~ /^-/ )
	{
	    $build_opt_list = [ $build_opt_list ];
	}

	else
	{
	    $build_opt_list = [ ];
	}
    }
    
    # Handle the options '--run' and '--timezone', if they were specified at the beginning of the
    # list. BuildCmd makes sure that they are placed there, but if this subroutine is called
    # directly it is the responsibility of the caller to put --run and/or --timezone at the
    # beginning if they are used at all. If both are specified, they can be in either order.
    
    my $opt_run = '';
    my $timezone;
    
    while ( @$build_opt_list )
    {
	if ( $build_opt_list->[0] =~ /^--run=(.*)/ )
	{
	    $opt_run = $1;
	    shift @$build_opt_list;
	    next;
	}
	
	elsif ( $build_opt_list->[0] =~ /^--timezone=(.*)/ )
	{
	    $timezone = $1;
	    shift @$build_opt_list;
	    next;
	}
	
	last;
    }

    # If we were given an explicit value for the timezone, use that even if it is the empty
    # string. An empty value will cause the container to use UTC (GMT) exclusively. Otherwise,
    # use the timezone specified in the configuration file.
    
    $timezone //= $CONFIG{local_timezone};
    
    # If the image name ends in _preload, then we are building a preload image. Note that there
    # may be a tag at the end, separated from the name by a colon.
    
    my $preload_build = $image_name =~ /_preload(:|$)/;
    
    # If the image name has no tag or has the tag 'latest', then we are building a new latest
    # image. But if the image name has a tag other than 'latest', set $tagged_build to true.
    
    $image_name =~ s/:latest$//;
    my $tagged_build = $image_name =~ /:/;
    
    # If we are building the main image for nginx, then check to see if Dockerfile-template is
    # newer than Dockerfile. If so, then rebuild the Dockerfile. We don't care if the contents
    # change or not.
    
    if ( $service eq 'nginx' && ! $preload_build )
    {
	my $result = BuildNginxDockerfile('ask');
	
	if ( $result && $result == -1 )
	{
	    print "\nThe nginx image cannot be built until an acceptable Dockerfile can be generated.\n\n";
	    return;
	}
	
	# my $project_data = ReadProjectData() || exit;
	
	# my $nginx_dockerfile = $CONFIG{nginx_dockerfile} || 'frontend/nginx/Dockerfile';
	# my $dockerfile_template = $CONFIG{nginx_dockerfile_template} || 'frontend/nginx/Dockerfile-template';
	
	# my %template_filename = ListComponentTemplates($project_data, "project/nginx-dockerfile-template");
	
	# my @other_templates = map { $project_data->{component_path}{$_} .
	# 				"/project/nginx-dockerfile-template.yml" } @installed_components;
	
	# my $generate_dockerfile = CheckTemplateTarget($nginx_dockerfile, undef,
	# 					      $dockerfile_template, @other_templates);
	
	# exit if $generate_dockerfile eq 'quit';

	# if ( $generate_dockerfile )
	# {
	#     my $dockerfile_sections = { };
	    
	#     # Read in all of the template files.
	    
	#     ReadTemplate($dockerfile_sections, $dockerfile_template, 'header');
	    
	#     foreach my $template_path ( @other_templates )
	#     {
	# 	if ( -e $template_path )
	# 	{
	# 	    ReadTemplate($dockerfile_sections, $template_path, $component);
	# 	}
	#     }
	    
	#     my $updated = GenerateFileFromTemplate($nginx_dockerfile, $dockerfile_sections,
	# 					   'header', @installed_components, 'final');

	#     # Read the file content, and do a basic check to make sure it is correct.
	    
	#     my $content = CaptureCommand('cat', $nginx_dockerfile);
	    
	#     unless ( $content && $content =~ /^FROM /m && $content =~ /^COPY /m &&
	# 	     $content =~ /^CMD |^ENTRYPOINT /m )
	#     {
	# 	print "ERROR: the newly generated contents of $nginx_dockerfile are invalid.\n";
		
	# 	if ( $updated && -e "$nginx_dockerfile.bak" )
	# 	{
	# 	    print "Restoring old version.\n";
	# 	    PrintDebug("rename $nginx_dockerfile.bak => $nginx_dockerfile") if $DEBUG;
	# 	    rename("$nginx_dockerfile.bak", $nginx_dockerfile);
	# 	}
	#     }
	    
	#     print "\n";
	# }
    }
    
    # Decode the contents of docker-compose.yml and docker-compose.override.yaml.
    
    my $compose_yaml = GetComposeYAML();
    
    # Determine the parameters for the build command using the specification from those files, or
    # print an error message and return.
    
    unless ( $compose_yaml->{services}{$service} &&
	     reftype $compose_yaml->{services}{$service} eq 'HASH' )
    {
	print "Cannot build an image for '$service': no compose entry found.\n";
	return;
    }
    
    my $entry = $compose_yaml->{services}{$service};
    
    unless ( $entry->{build} )
    {
	print "Cannot build an image for '$service', because it has no build section.\n";
	return;
    }
    
    my $context = $entry->{build}{context} || '.';
    my $dockerfile_relative = $entry->{build}{dockerfile} || 'Dockerfile';
    
    my $dockerfile = "$context/$dockerfile_relative";
    $dockerfile =~ s{^[.][/]}{};
    
    # If this is a preload build, add the suffix -preload to the dockerfile name.
    
    if ( $preload_build )
    {
	$dockerfile = "$dockerfile-preload";
    }
    
    # Otherwise, this is a container image build. So add any necessary build arguments.
    
    else
    {
	# If a timezone has been specified for the container, and it is not UTC, then pass that in
	# as the build argument TZ. The container will default to UTC if no build argument is
	# specified.
	
	if ( $timezone && $timezone !~ qr{ \b UTC $ }xsi )
	{
	    unshift @$build_opt_list, '--build-arg', "TZ=$timezone";
	}
    }
    
    # Not being able to read the dockerfile is a fatal error.
    
    unless ( -r $dockerfile )
    {
	print "ERROR: cannot read $dockerfile: $!\n";
	return;
    }
    
    # Put together the build command. We use 'docker build' rather than 'docker-compose build'
    # because the former provides much better error messages and a wider set of build options. The
    # docker-compose build command often returns useless error messages and doesn't tell you what
    # actually went wrong.
    
    my @build_command = ('docker', 'build', '-t', $image_name, '-f', $dockerfile,
			 @$build_opt_list, $context);
    
    # If we are building a new latest version, assign the tag 'previous' to the current latest
    # version if there is one. That will allow it to be restored if the buildcheck fails.
    # Regardless of whether or not this is a latest build, if there is an existing image under
    # this name, remember its id for later.
    
    my $new_id;
    
    if ( FindImage("$image_name:latest") && ! $tagged_build )
    {
	SystemCommand('docker', 'tag', "$image_name:latest", "$image_name:previous");
    }
    
    # Now execute the build command.
    
    print "Building image '$image_name' for '$service' using the following command:\n";
    print join(' ', @build_command) unless $DEBUG;
    print "\n\n";
    
    my $result = SystemCommand(@build_command);
    
    # If the build is unsuccessful, then return false. Otherwise, inform the user that the build
    # succeeded. For an unsuccessful build, remove the 'previous' tag if it points to the same
    # image as 'latest'.
    
    if ( ! $result )
    {
	CleanUpPrevious($image_name);
	print "\nThe build of image $image_name failed.\n\n";
	return;
    }
    
    else
    {
	$new_id = GetImageID($image_name);
	print "\nThe build of image $image_name succeeded. New image id: $new_id\n\n";
    }
    
    # If --run=nocheck was specified, return true immediately.
    
    if ( $opt_run eq 'nocheck' )
    {
	CleanUpPrevious($image_name);
	return 1;
    }
    
    # Otherwise, we proceed according to the type of build this is. If we have built a latest
    # preload image, then we ask if the user wishes to test it by building the corresponding main
    # image. For any other preload image, we just return true.
    
    elsif ( $preload_build )
    {
	return 1 if $tagged_build;
	
	my $proceed = AskQuestion("Do you want to test it by building the main image for '$service'? [y/n] ",
			      { yesno => 1 });
	
	print "\n";
	
	return 1 if $proceed eq 'no';
	
	# If the user answers yes, then generate the name for a test image.
	
	my $test_name = $image_name;
	$test_name =~ s/_preload.*//;
	$test_name .= ':test' unless $test_name =~ /:test$/;
	
	# If the test image builds successfully and is accepted, then return true. The test image is
	# built without any build options, because we really have no way for the user to specify
	# them.

	my $test_result = BuildImage($service, $test_name);
	
	SystemCommand('docker', 'rmi', $test_name);
	
	print "\n";
	
	if ( $test_result )
	{
	    CleanUpPrevious($image_name);
	    return 1;
	}
    }
    
    # If we have built a main image, then we check for a 'buildcheck' label in it. If one exists,
    # we use its value in an attempt to ascertain whether this new build is acceptable. We make
    # this check for all new images, not just latest ones. If the buildcheck succeeds or if no
    # buildcheck is defined, then we return true.
    
    elsif ( CheckBuild($image_name) )
    {
	print "\n";
	
	return 1 if $tagged_build;
	
	# If the new image is acceptable, and this is not a tagged build, then check for
	# containers that use the old version and ask the user whether to destroy them.
	
	if ( FindImage("$image_name:previous") )
	{
	    StopRunningContainers("$image_name:afterbuild", $opt_run || 'restart');
	}
	
	CleanUpPrevious($image_name);
	return 1;
    }
    
    # If we get here, it means that the new image was judged unacceptable. If the user wants to
    # save the bad image for later analysis, they can enter a tag name. Otherwise, it is deleted.
    
    my $save_tag = AskQuestion("If you wish to save this bad image, enter a tag name: ",
			   { optional => 1 });
    
    if ( $save_tag )
    {
	SystemCommand('docker', 'tag', $image_name, "$image_name:$save_tag");
    }
    
    else
    {
	SystemCommand('docker', 'rmi', $image_name);
    }
    
    # If we were trying to build a latest image and a previous image exists for it, then retag
    # 'previous' as 'latest'.
    
    unless ( $tagged_build )
    {
	if ( FindImage("$image_name:previous") )
	{
	    print "Tagged: $image_name:previous => latest.\n";
	    SystemCommand('docker', 'tag', "$image_name:previous", "$image_name:latest");
	    SystemCommand('docker', 'rmi', "$image_name:previous");
	}
    }
    
    # Now return false, because the image was rejected.
    
    return;
}


# CleanUpPrevious ( image_name )
#
# If the previous and latest versions of the specified image point to the same image id, remove
# the 'previous' tag.

sub CleanUpPrevious {

    my ($image_name) = @_;
    
    my $latest = GetImageID("$image_name:latest");
    my $previous = GetImageID("$image_name:previous");
    
    if ( $latest && $previous && $latest eq $previous )
    {
	SystemCommand('docker', 'rmi', "$image_name:previous");
    }
}



# CheckBuild ( image )
#
# If the the specified image was built with the label "buildcheck", run the value of that label as
# a command in a new container built using that image. Then ask the user whether the image is
# acceptable. This is not a judgement that can be made automatically, but the user should be able
# to determine if the command succeeds or fails. This can be as simple as a syntax check of the
# container entrypoint command, or actually running it to test that it actually functions
# properly.

sub CheckBuild {
    
    my ($image_name) = @_;
    
    unless ( $image_name =~ /_(\w+)/ )
    {
	die "Error: no service name found.\n";
    }

    my $service = $1;
    
    my $info = CaptureCommand('docker', 'inspect', $image_name);
    
    if ( $info =~ / ^ \s* "? buildcheck "? \s* : \s* " (.+) ", \s* $ /xm )
    {
	my $check_cmd = $1;
	my $run_container = "${image_name}_buildcheck";
	$run_container =~ s/:/_/;
	
	# We use 'docker-compose run' to create the container and run the command instead of
	# 'docker run' because docker-compose will configure the container with the proper mounted
	# volumes and network.
	
	if ( $check_cmd eq 'sh' )
	{
	    print "An interactive shell will be run in container $run_container.\n";
	    print "Do whatever is necessary to determine whether this image is acceptable,\n";
	    print "and then exit the shell:\n\n";
	    
	    SystemDockerCompose('run', '--rm', '--name', $run_container, $service, 'sh');
	}
	
	else
	{
	    print "Running build check command \"$check_cmd\" in container $run_container:\n\n";
	    
	    SystemDockerCompose('run', '--rm', '--name', $run_container, $service, 'sh', '-c', $check_cmd);
	}
	
	print "\n";
	
	my $proceed = AskQuestion("Based on the above output, is this new image acceptable? [y/n] ", { yesno => 1 });
	
	print "\n";
	
	return $proceed eq 'yes' ? 1 : 0;
    }
    
    else
    {
	print "\nNo build check was included in this image.\n\n";
	return 1;
    }
}


# StopRunningContainers ( image_name, run_option )
# 
# Stop and remove all containers running with the specified image. If the image name is a latest
# version, also stop and remove any container whose name matches the image name. This will take
# down the running service even if it is associated with a different version of the image.
# 
# If the run option is 'yes', then start the service. If it is 'restart', then start the service
# only if a container previously existed for it and its status was 'up'. If it is 'ask', then
# ask the user what they want to do.

sub StopRunningContainers {
    
    my ($image_name, $opt_run) = @_;
    
    my $latest_name;
    my $tagged_build;
    
    if ( $image_name =~ /^(.*):afterbuild$/ )
    {
	$image_name = "$1:previous";
	$latest_name = $1;
    }
    
    elsif ( $image_name =~ /^(.*):latest$/ )
    {
	$latest_name = $1;
    }
    
    elsif ( $image_name !~ /:/ )
    {
	$latest_name = $image_name;
    }

    else
    {
	$tagged_build = 1;
    }
    
    my @lines = CaptureCommand('docker', 'ps', '--all', '--filter', "ancestor=$image_name", '--format',
		    '{{.Label "com.docker.compose.service"}}::{{.Status}}::{{.Names}}::{{.ID}}::{{.CreatedAt}}');

    if ( $latest_name )
    {
	push @lines, CaptureCommand('docker', 'ps', '--all', '--filter', "name=$latest_name", '--format',
		    '{{.Label "com.docker.compose.service"}}::{{.Status}}::{{.Names}}::{{.ID}}::{{.CreatedAt}}');
    }
    
    chomp @lines;
    
    # If there are any matching containers, go through the list. Separate out containers that
    # correspond to services from others, and present them last.
    
    my $service_status;
    
    print "\The following containers use the image $image_name:\n" if @lines;
    
    my (@containers, @services, %found, @destroy);
    
    foreach my $line ( @lines )
    {
	if ( $line =~ /^::/ )
	{
	    push @containers, $line;
	}
	
	else
	{
	    push @services, $line;
	}
    }
    
    foreach my $line ( @containers, @services )
    {
	my ($service, $status, $name, $id, $created) = split /::/, $line;
	
	$name ||= $id;
	
	# Skip containers we have already listed.
	
	next if $found{$id};
	$found{$id} = 1;

	push @destroy, $line;
	
	if ( $service )
	{
	    print "  Service container $name, $status, started $created\n";
	    $service_status = $status;
	}
	
	else
	{
	    print "  Container $name, $status, started $created\n";
	}
    }
    
    # If the run option is 'ask', then ask before destroying.

    if ( ($opt_run eq 'ask') && @destroy )
    {
	print "\n";
	
	my $answer = AskQuestion("Stop and remove these containers? [y/n] ", { yesno => 1 });
	
	return unless $answer eq 'yes';

	print "\n";
    }
    
    # Otherwise, stop and remove these containers one by one.
    
    foreach my $line ( @destroy )
    {
	my ($service, $status, $name, $id, $created) = split /::/, $line;
	
	$name ||= $id;

	print "Stopping ";
	SystemCommand('docker', 'stop', $name);
	print "Removing ";
	SystemCommand('docker', 'rm', $name);
    }
    
    # If we know we are not going to start the service, return now.
    
    if ( ! $opt_run || $opt_run eq 'no' || $opt_run eq 'nocheck' || $tagged_build )
    {
	return 1;
    }
    
    # Determine the service name from the image, if possible.
    
    my $service_name;
    
    if ( $latest_name && $latest_name =~ /_(\w+)/ )
    {
	$service_name = $1;
    }
    
    else
    {
	print "\nImage name '$image_name' is not associated with a service. Nothing to start.\n\n";
	return 1;
    }
    
    # Now decide whether to start the service, based on the run option.
    
    if ( $opt_run eq 'restart' )
    {
	unless ( $service_status && $service_status =~ /up/i )
	{
	    print "\nService '$service_name' was not running, so will not be started.\n\n";
	    return 1;
	}
    }
    
    elsif ( $opt_run eq 'ask' )
    {
	my $answer = AskQuestion("Start service $service_name? [y/n] ", { yesno => 1 });
	return 1 unless $answer eq 'yes';
    }

    elsif ( $opt_run eq 'yes' )
    {
	print "\nStarting service '$service_name':\n";
    }
    
    else
    {
	print "Ignoring run option '$opt_run'.\n";
	return 1;
    }
    
    SystemDockerCompose('up', '-d', '--no-build', $service_name);
    sleep(2);
    DisplayStatus($service_name);
    SystemDockerCompose('logs', '--tail', '15', $service_name);
    
    print "\n";
    
    return 1;
}


# CopyCmd ( )
#
# This routine implements the subcommands 'copyin' and 'copyto'.

$LDOC{copyin} = <<EndCopyIn;

Usage:  {NAME} copyin [OPTIONS] [container:] pathname...

This command copies files or file trees into all running containers whose images would
include those files if built. The files are copied into the locations where they would
go if the container images were immediately rebuilt. This is useful for development,
allowing you to edit files on the outside and copy the edited versions into running
containers without having to rebuild the images. You are responsible for restarting the
individual containers if that is necessary for your changes to take effect.

The map from path names in the outside filesystem to path names in the container images
is extracted from docker-compose.yml and the individual Dockerfiles, and is stored in
the file .copymap in the main project directory. Whenever you edit the compose file
or a dockerfile, rerun this command with the option --remap to recompute this map.

Options:

  --remap, -r               Rebuild the map of outside paths to container image paths
  
  --monitor, -m             After copying the specified file tree(s), stay running and
                            scan them every few seconds for modified files. Whenever
                            modified files are found, copy them immediately into the
                            mapped container(s).

EndCopyIn

$LDOC{copyto} = <<ENDCopyTo;

Usage:  {NAME} copyto [OPTIONS] container pathname...

This command copies files or file trees into the specified container. Unless you explicitly
specify the --target option, the Dockerfile that was used to build the container image is located
and searched for COPY directives. For each pathname specified on the command line, if it matches
or is located within the source of a COPY directive, then the files are copied to the
corresponding target location in the container. If you specify the --monitor option, the command
continues to run and scans those file trees every few seconds. Whenever a file is modified, it is
immediately copied to the container. This can be used to facilitate development and testing, using
an external editor while immediately causing all saved changes to be copied into the container.

The container can be specified either as a service name or a container name or identifier.

Options:

  --target=PATH, -t          Copy the specified files or file trees to the specified path in the
                               target container.
  --monitor, -m              Stay running and scan the copied file trees for modified files. When
                               any are found, copy them immediately into the container.

ENDCopyTo

sub CopyCmd {
    
    my $cmd = shift @ARGV;
    
    die "ERROR: you must specify at least one pathname to copy.\n"
	unless @ARGV;
    
    # We want to allow options either before or after the service name. If the next word on the
    # command line doesn't start with - and ends with :, assume it is a container or service name
    # and look for options after that.
    
    my $container; $container = shift @ARGV if $ARGV[0] =~ /^[^-].*:$/;
    
    my ($opt_remap, $opt_monitor);
    
    GetOptions( "r|remap" => \$opt_remap,
		"m|monitor" => \$opt_monitor );
    
    $container ||= shift @ARGV if $ARGV[0] =~ /:$/;

    # If the --remap option was given, remap now.

    if ( $opt_remap )
    {
	return &RebuildCopyMap;
    }
    
    # Otherwise, check that we were given at least one pathname, and that
    # they all exist and are readable.
    
    my @pathnames = @ARGV;
    
    die "ERROR: you must specify at least one pathname to copy.\n" unless @pathnames;
    
    my $workdir = getcwd();
    
    foreach my $path (@pathnames)
    {
	die "ERROR: $path: $!\n" unless -r "$workdir/$path";
	$path = "$workdir/$path";
    }
    
    chdir $MAIN_PATH || die "ERROR: could not chdir to $MAIN_PATH: $!\n";
    
    # Now check the container specification. It may contain more than one name, separated by
    # commas. If so, all specified files are copied into any containers they match. This can
    # be used, for example, in the case where the webserver and some other service both have
    # access to a common set of files.

    my $container_re;
    
    if ( $container )
    {
	$container =~ s/:$//;
	$container_re = qr{$container};
    }
    
    # Get the list of currently running containers, and search through them to match all specified
    # names. If no names were specified, use all running containers.
    
    my @lines = CaptureCommand('docker', 'ps', '--all', '--format',
			       '{{.Names}}::{{.Label "com.docker.compose.service"}}::{{.Status}}');
    
    chomp @lines;
    
    my %container_map;
    
  NAME:
    foreach my $ps (@lines)
    {
	next unless $ps;
	
	if ( $container_re )
	{
	    next unless $ps =~ $container_re;
	}
	
	my ($name, $service, $status) = split /::/, $ps;
	
	# unless ( $status =~ /up/i )
	# {
	#     print "Container '$name' is not currently running.\n";
	#     next;
	# }
	
	$container_map{$service} ||= [ ];
	push @{$container_map{$service}}, $name;
    }

    unless ( %container_map )
    {
	print "No matching containers are running.\n";
	return;
    }
    
    # Now we read in the .copymap file and look through it to figure out which paths we are
    # copying.
    
    my (%path_map, %monitor, %monitor_service);
    
    open( my $infile, '<', "$MAIN_PATH/.copymap" ) || die "Could not read .copymap: $!\n";
    
    while ( my $line = <$infile> )
    {
	chomp $line;
	my ($service, $source, $dest) = split(/\t/, $line);
	
	$path_map{$service}{$source} = $dest;
    }

    my $copy_count;
    
    foreach my $service (sort keys %container_map)
    {
	my @containers = @{$container_map{$service}};
	
	my $map = $path_map{$service};
	my $service_copy_count;

	PrintDebug("Checking service $service...") if $DEBUG;
	
	foreach my $source_path (@pathnames)
	{
	    my $is_file = -f $source_path ? 1 : undef;
	    
	    unless ( $is_file )
	    {
		$source_path =~ s{ /[.]? $ }{}xs;
	    }
	    
	    foreach my $match_path ( keys %$map )
	    {
		if ( $match_path eq substr($source_path, 0, length($match_path)) )
		{
		    PrintDebug("  MATCHED $match_path <= $source_path") if $DEBUG;
		    
		    $monitor{$source_path} = 1 if $opt_monitor;
		    $monitor_service{$service} = 1 if $opt_monitor;
		    
		    my $remainder = substr($source_path, length($match_path) + 1);
		    my $dest_path = $map->{$match_path} . '/' . $remainder;
		    unless ( $is_file )
		    {
			$source_path .= "/" unless $source_path =~ qr{/$};
			$source_path .= ".";
		    }
		    
		    foreach my $container (@containers)
		    {
			print "Copying $source_path => $container:$dest_path\n";
			
			SystemCommand("docker cp $source_path $container:$dest_path");
			$service_copy_count++;
		    }
		}

		elsif ( $DEBUG )
		{
		    PrintDebug("  $match_path");
		}
	    }
	}

	if ( $DEBUG && ! $service_copy_count )
	{
	    PrintDebug("Nothing to copy for $service");
	}
    }
    
    unless ( $copy_count )
    {
	print "Nothing to copy.\n";
    }
    
    # Now, if --monitor was specified, we start monitoring the copied files.
    
    return unless $opt_monitor;

    my @monlist = sort keys %monitor;
    
    if ( @monlist == 1 )
    {
	print "Monitoring $monlist[0] for modified files...\n";
    }

    else
    {
	print "Monitoring the following file trees for modified files...\n";
	print "   $_\n" foreach @monlist;
    }
    
    # my $tracefile = "$MAIN_PATH/.copy$$";
    # SystemCommand("touch $tracefile");
    
    # $SIG{INT} = $SIG{HUP} = sub { unlink "$MAIN_PATH/.copy$$"; die "Monitoring ends.\n"; };
    
    my %copied_mtime;
    my %dir_exists;
    
    while ( 1 )
    {
	sleep(2);
	
	# my $mtime = time - 60;
	# utime $mtime, $mtime, $tracefile;
	
	my @lines;
	
	foreach my $path (@monlist)
	{
	    push @lines, CaptureCommand("find $path -name .git -prune -o -mmin 1 -print");
	    # push @lines, CaptureCommand("find $path -name .git -prune -o -newer $tracefile -print");
	}

	chomp @lines;
	
	my @tocopy;
	my %new_mtime;
	
	foreach my $entry (@lines)
	{
	    # next if $monitor{$entry};
	    
	    my $mtime = (stat ($entry))[9];
	    
	    unless ( ! $dir_exists{$entry} && $copied_mtime{$entry} && $copied_mtime{$entry} eq $mtime )
	    {
		push @tocopy, $entry;
		$new_mtime{$entry} = $mtime;
	    }
	}
	
	next unless @tocopy;
	
	foreach my $service (sort keys %monitor_service)
	{
	    my $map = $path_map{$service};
	    my @containers = @{$container_map{$service}};
	    
	    foreach my $source_path (@tocopy)
	    {
		foreach my $match_path ( keys %$map )
		{
		    if ( $match_path eq substr($source_path, 0, length($match_path)) )
		    {
			PrintDebug("$match_path <= $source_path", "Matched") if $DEBUG;
			
			my $remainder = substr($source_path, length($match_path) + 1);
			my $dest_path = $map->{$match_path};
			$dest_path .= '/' unless $dest_path =~ qr{/$};
			$dest_path .= $remainder;

			foreach my $container ( @containers )
			{
			    if ( -d $source_path )
			    {
				my $check = CaptureCommand("docker exec $container ls -d $dest_path");
				
				if ( $check )
				{
				    $dir_exists{$source_path} = 1;
				}
				
				else
				{
				    print "Creating directory $container:$dest_path\n" unless $DEBUG;
				    SystemCommand("docker cp $source_path $container:$dest_path");
				    $dir_exists{$source_path} = 1;
				}
			    }
			    
			    else
			    {
				print "Copying $source_path to $container:$dest_path\n" unless $DEBUG;
				SystemCommand("docker cp $source_path $container:$dest_path");
				$copied_mtime{$source_path} = $new_mtime{$source_path};
			    }
			}
		    }
		}
	    }
	}
    }
}


sub RebuildCopyMap {

    chdir($MAIN_PATH) || die "Could not chdir to $MAIN_PATH: $!\n";
    
    my %path_map;
    my %dup_map;
    my @map_list;
    
    my $compose_yaml = GetComposeYAML();

  SERVICE:
    foreach my $service ( keys %{$compose_yaml->{services}} )
    {
    	if ( $compose_yaml->{services}{$service} &&
	     reftype $compose_yaml->{services}{$service} eq 'HASH' )
	{
	    my $entry = $compose_yaml->{services}{$service};
	    
	    if ( $entry->{build} && ($entry->{build}{dockerfile} || $entry->{build}{context}) )
	    {
		my $dockerfile = $entry->{build}{dockerfile} || 'Dockerfile';
		my $base = $MAIN_PATH;
		$base = $entry->{build}{context} if $entry->{build}{context};
		
		PrintDebug("$base/$dockerfile", "Scanning") if $DEBUG;

		unless ( -r "$base/$dockerfile" )
		{
		    print "WARNING: could not read $base/$dockerfile: $!\n";
		    next SERVICE;
		}
		
		my @content = CaptureCommand("cat $base/$dockerfile");
		
		chomp @content;
		
		foreach my $line (@content)
		{
		    if ( $line =~ qr{ ^ \s* COPY \s+ ( .* ) }xsi )
		    {
			my @paths = split(/\s+/, $1);

			my $dest = pop @paths;
			my ($mult_source, $dest_has_slash);
			
			next unless @paths;

			if ( @paths > 1 )
			{
			    $mult_source = 1;
			}
			
			if ( $dest =~ qr{ /$ }xs )
			{
			    $dest_has_slash = 1;
			    $dest =~ s{ /$ }{}xs;
			}
			
			foreach my $source ( @paths )
			{
			    $source =~ s{ ^./ }{}xs;
			    $source =~ s{ /$ }{}xs;
			    $source = "$base/$source";
			    
			    if ( $mult_source || ( ! -d $source && $dest_has_slash ) )
			    {
				$source =~ qr{ ( [^/]+ ) $ }xs;
				$path_map{$service}{$source} = "$dest/$1";
				push @map_list, "$service\t$source\t$dest/$1\n";
			    }
			    
			    else
			    {
				$path_map{$service}{$source} = $dest;
				push @map_list, "$service\t$source\t$dest\n";
			    }
			    
			    PrintDebug("[$service] $source => $path_map{$service}{$source}", "Mapping") if $DEBUG;
			}
		    }
		}
	    }
	    
	    elsif ( $entry->{image} && $entry->{image} =~ / ^ paleobiodb_ (.*) /xs )
	    {
		my $source = $1;
		PrintDebug("map from $source to $service", "Duplicating");
		$dup_map{$service} = $source;
	    }
	    
	    else
	    {
		PrintDebug($service, "Skipping");
	    }
	}
    }
    
    # Now do all the necessary duplications.
    
    foreach my $service ( keys %dup_map )
    {
	my $from = $dup_map{$service};

	foreach my $source ( keys %{$path_map{$from}} )
	{
	    my $dest = $path_map{$from}{$source};
	    PrintDebug("[$service] $source => $dest", "Mapping") if $DEBUG;
	    push @map_list, "$service\t$source\t$dest\n";
	}
    }
    
    # Now write out the path map.

    open( my $outfile, '>', "$MAIN_PATH/.copymap" ) || die "Could not write $MAIN_PATH/.copymap: $!\n";

    print $outfile @map_list;

    close $outfile || die "Could not write $MAIN_PATH/.copymap: $!\n";
}


# PushPullCmd ( )
#
# Either push or pull the specified image, or the image running in the container corresponding to
# the specified service, to the repository specified in the configuration file.

$LDOC{push} = <<EndPush;

Usage:  {NAME} push [IMAGE or SERVICE]

Push the specified preload image, or the preload image for the specified
service, to the registry specified in 'config.yml' under the key
'docker_registry'.

EndPush

$LDOC{pull} = <<EndPull;

Usage:  {NAME} pull [IMAGE or SERVICE]

Pull the specified preload image, or the preload image for the specified
service, to the registry specified in 'config.yml' under the key
'docker_registry'.

EndPull

sub PushPullCmd {
    
    my $cmd = shift @ARGV;
    
    ReadLocalConfig;
    
    my $registry;
    my $regname;
    
    GetOptions("registry=s", \$registry);
    
    # if ( $COMMAND eq 'macrostrat' )
    # {
    # 	$registry ||= $CONFIG{macro_registry};
    # 	$regname = 'macro_registry';
    # }
    
    # else
    # {
    # 	$registry ||= $CONFIG{pbdb_registry};
    # 	$regname = 'pbdb_registry'
    # }
    
    # die "ERROR: you must specify a remote registry either with the configuration option '$regname' or with the option '--registry'\n"
    # 	unless $registry;
    
    # die "ERROR: invalid registry name '$registry' - must contain at least one slash\n"
    # 	unless $registry =~ qr{/};
    
    my @services = GetComposeServices(@ARGV);
    my @images;
    
    die "ERROR: you must specify one or more services.\n"
	unless @ARGV;
    
    my @registry_list;
    my %image_list;
    
    foreach my $service ( @services )
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
	PushPullImages($cmd, $registry, @{$image_list{$registry}});
    }
}


sub PushPullImages {

    my ($cmd, $registry, @image_tags) = @_;

    if ( @image_tags )
    {
	my $image_list = join(', ', @image_tags);
	
	print "\nPulling from $registry: $image_list\n";
    }

    else
    {
	print "\nNothing to pull from $registry\n";
	return;
    }
    
    # We must first log in to the registry.
    
    print "\nLogging in to $registry:\n";
    
    my $tries = 3;
    my $result;
    
    while ( $tries-- )
    {
	$result = SystemCommand("docker", "login", $registry);
	last if $result;
	print "Invalid username or password. Please try again.\n";
    }

    unless ( $result )
    {
	print "\nAborted after three failed tries.\n";
	return;
    }
    
    # Now process each specified image
    
    foreach my $image ( @image_tags )
    {
	my $registry_tag = "$registry/$image";
	
	# If the command was 'push', then tag the image as "registry/image_name" and push it to
	# the remote registry.
	
	if ( $cmd eq 'push' )
	{
	    SystemCommand('docker', 'tag', $image, $registry_tag);
	    SystemCommand('docker', 'push', $registry_tag);
	}
	
	# If the command was 'pull', then do the opposite. Pull the image "registry/image_name",
	# then give it the local tag "image_name".
	
	elsif ( $cmd eq 'pull' )
	{
	    SystemCommand('docker', 'pull', $registry_tag);
	    SystemCommand('docker', 'tag', $registry_tag, $image);
	}
    }
    
    # Then log back out from the registry, so our login information is not stored in plaintext.
    
    print "Logging out of $registry.\n";
    SystemCommand("docker", "logout", $registry);
}


# BuildNginxDockerfile ( mode )
#
# If $mode is 'force', then build the nginx Dockerfile from the templates specified in the base
# repository and the installed project components. Otherwise, rebuild it only if any of those
# templates are newer. If $mode is 'ask', then ask the user if they want to proceed with
# rebuilding the file. Otherwise, rebuild it without asking.

sub BuildNginxDockerfile {

    my ($mode) = @_;
    
    # Make sure that the local configuration file and project data file have been read in.
    
    ReadLocalConfig();
    ReadComponentData();
    
    # my $nginx_dockerfile = $CONFIG{nginx_dockerfile} || 'frontend/nginx/Dockerfile';
    # my $dockerfile_template = $CONFIG{nginx_dockerfile_template} || 'frontend/nginx/Dockerfile-template';
    # my $template_path = $CONFG{component_nginx_template} || 'project/nginx-dockerfile-template';
    
    # Generate a list of template files from the installed project components.
    
    my %template_filename = ListComponentTemplates($CONFIG{component_nginx_template});
    
    # If $mode is 'force' then go right to building the target file. Otherwise, check all of the
    # source templates. CheckTemplateTarget returns 'quit' if the user was asked and answered 'q'
    # or 'quit'. Otherwise, it returns true if one or more of the templates is newer than the
    # target, false otherwise. The user is only asked if $mode is 'ask'.
    
    unless ( $mode && $mode eq 'force' )
    {
	my $ask = $mode && $mode eq 'ask' ? 1 : undef;
	
	my $generate_target = CheckTemplateTarget($CONFIG{nginx_dockerfile}, $ask,
						  $CONFIG{nginx_dockerfile_template},
						  values %template_filename);
	
	exit if $generate_target eq 'quit';

	unless ( $generate_target )
	{
	    print "\n - FILE $CONFIG{nginx_dockerfile} is up to date\n";
	    return 0;
	}
    }
    
    # Read in all of the template files.
    
    my $dockerfile_sections = { };
    
    ReadTemplate($dockerfile_sections, $CONFIG{nginx_dockerfile_template}, 'header');
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	if ( $template_filename{$component} )
	{
	    ReadTemplate($dockerfile_sections, $template_filename{$component}, $component);
	}
    }
    
    # Filter the list of installed components, selecting only those for which we have found a
    # section.
    
    my @dockerfile_components = grep { $dockerfile_sections->{$_} } @INSTALLED_COMPONENTS;
    
    # Now generate the new file.
    
    my $updated = GenerateFileFromTemplate($CONFIG{nginx_dockerfile}, $dockerfile_sections,
					   'header', @dockerfile_components, 'final');
    
    # Read the new file content, and do a basic check to make sure it is correct.
    
    my $content = CaptureCommand('cat', $CONFIG{nginx_dockerfile});
    
    unless ( $content && $content =~ /^FROM /m && $content =~ /^COPY /m &&
	     $content =~ /^CMD |^ENTRYPOINT /m )
    {
	print "\nERROR: the newly generated contents of $CONFIG{nginx_dockerfile} are invalid.\n";
	
	if ( $updated && -e "$CONFIG{nginx_dockerfile}.bak" )
	{
	    print "Restoring old version.\n";
	    PrintDebug("rename $CONFIG{nginx_dockerfile}.bak => $CONFIG{nginx_dockerfile}") if $DEBUG;
	    rename("$CONFIG{nginx_dockerfile}.bak", $CONFIG{nginx_dockerfile});
	    
	    return -1;
	}
    }
    
    return 1;
}


# ReadComponentData ( )
# 
# Read YAML data from the component data files in the main repository and all subsidiary
# repositories. If component-data.override.yml exists in the main directory, its entries override
# those in the other files.

sub ReadComponentData {
    
    my ($options) = @_;
    
    # If we have already gathered and cached the component data, just return unless the
    # 'no_cache' option was given. If we have at least one component path, we know that
    # the data was properly loaded.
    
    if ( %COMPONENT && ! $options->{no_cache} )
    {
	foreach my $k ( keys %COMPONENT )
	{
	    return 1 if $COMPONENT{$k}{path};
	}
    }
    
    my $read_options = { }; $read_options->{no_cache} = 1 if $options->{no_cache};
    
    # Read the local configuration file if it hasn't been read yet.
    
    ReadLocalConfig() unless %CONFIG;
    
    # Make sure we have the necessary configuration values.

    die "ERROR: 'main_component_data' is not defined.\n" unless $CONFIG{main_component_data};
    die "ERROR: 'local_component_data' is not defined.\n" unless $CONFIG{local_component_data};
    
    # Now read the main component data file.
    
    my $component_data = ReadConfigFile("$MAIN_PATH/$CONFIG{main_component_data}", $read_options) ||
	die "ERROR: could not read $CONFIG{main_component_data}. Aborting.\n";
    
    unless ( ref $component_data->{component} eq 'HASH' && %{$component_data->{component}} )
    {
	die "ERROR: 'component:' not found in $CONFIG{main_component_data}.\n";
    }
    
    # If the override file exists, read that too. It is okay if it has no content, but if an error
    # occurs while reading it then return false.
    
    my $component_override;
    
    $read_options->{empty_ok} = 1;
    
    if ( -e "$MAIN_PATH/$CONFIG{local_component_data}" )
    {
	$component_override = ReadConfigFile("$MAIN_PATH/$CONFIG{local_component_data}", $read_options);
	$component_override->{component} ||= { };
    }
    
    elsif ( $DEBUG )
    {
	PrintDebug("Skipping $CONFIG{local_component_data}: not found");
    }
    
    # Then go through all of the project components from the main component data file and the override
    # file.
    
    foreach my $component ( keys %{$component_data->{component}} )
    {
	if ( $CONFIG{"include_$component"} eq 'yes' &&
	     ref $component_data->{component}{$component} eq 'HASH' &&
	     $component_data->{component}{$component}{path} )
	{
	    $COMPONENT{$component} = $component_data->{component}{$component};
	}
    }
    
    foreach my $component ( keys %{$component_override->{component}} )
    {
	if ( $CONFIG{"include_$component"} eq 'yes' &&
	     ref $component_override->{component}{$component} eq 'HASH' &&
	     $component_override->{component}{$component}{path} )
	{
	    $COMPONENT{$component}{path} = $component_override->{component}{$component}{path};
	}
    }
    
    # Read any component data files that exist. If they contain an entry corresponding to their own
    # component, substitute it into the component data hash.
    
    foreach my $component ( keys %COMPONENT )
    {
	if ( my $component_path = $COMPONENT{$component}{path} )
	{
	    my $component_datafile = "$MAIN_PATH/$component_path/$CONFIG{component_data_file}";
	    
	    if ( -e $component_datafile )
	    {
		my $local_data = ReadConfigFile($component_datafile, $read_options);
		
		if ( ref $local_data eq 'HASH' && ref $local_data->{component} eq 'HASH' &&
		     ref $local_data->{component}{$component} eq 'HASH' &&
		     %{$local_data->{component}{$component}} )
		{
		    PrintDebug("Incorporating component '$component' from $component_datafile")
			if $DEBUG;
		    $COMPONENT{$component} = $local_data->{component}{$component};
		}
		
		elsif ( ref $local_data eq 'HASH' && ref $local_data->{$component} eq 'HASH' &&
			%{$local_data->{$component}} )
		{
		    PrintDebug("Incorporating component '$component' from $component_datafile")
			if $DEBUG;
		    $COMPONENT{$component} = $local_data->{$component};
		}
		
		# Make sure the path isn't overwritten. The component data file in the component
		# directory shouldn't specify the path, but should be ignored if it does.
		
		$COMPONENT{$component}{path} = $component_path;
	    }
	}
    }
    
    # Construct a list of installed components in the specified order. Create a separate list of
    # database components and webserver components.
    
    my @known_components;
    
    if ( ref $component_data->{'component-order'} eq 'ARRAY' )
    {
	@known_components = @{$component_data->{'component-order'}};
    }
    
    if ( ref $component_override->{'component-extra'} eq 'ARRAY' )
    {
	push @known_components, @{$component_data->{'component-extra'}};
    }
    
    my %uniq;
    
    @INSTALLED_COMPONENTS = ();
    
    foreach my $component ( @known_components )
    {
	if ( $COMPONENT{$component} && $CONFIG{"include_$component"} eq 'yes' &&
	     ! $uniq{$component} )
	{
	    push @INSTALLED_COMPONENTS, $component;
	    push @DB_COMPONENTS, $component if $COMPONENT{$component}{is_database};
	    push @WS_COMPONENTS, $component if $COMPONENT{$component}{is_webserver};
	    $uniq{$component} = 1;
	}
    }
    
    # Subsittute any data found in the override file. Entries are not substituted entire, but
    # rather their subkeys are substituted in a recursive manner. Any components not already
    # listed are added to @INSTALLED_COMPONENTS in order.
    
    foreach my $component ( sort keys %{$component_override->{component}} )
    {
	if ( ref $component_override->{component}{$component} eq 'HASH' )
	{
	    PrintDebug("Overriding component '$component' from $MAIN_PATH/$CONFIG{local_component_data}")
		if $DEBUG;
	    
	    OverrideRecursive($COMPONENT{$component}, $component_override->{component}{$component});

	    push @INSTALLED_COMPONENTS, $component unless $uniq{$component};
	}
    }

    # Add configuration file entries to @COMPONENT_CONF.
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	if ( ref $COMPONENT{$component}{config_files} eq 'ARRAY' )
	{
	    foreach my $entry ( @{$COMPONENT{$component}{config_files}} )
	    {
		$entry->{component} = $component;
		push @COMPONENT_CONF, $entry;
	    }
	}
    }
    
    # If Install.pm is included, fill in the @MAIN_CHOICE array. If a 'main-choice' entry is included in
    # the override file, use that. Otherwise, default to the entry in the main component data file.
    
    if ( %PMCmd::Install::INSTALL_STEP )
    {
	if ( ref $component_override->{'main-choice'} eq 'ARRAY' )
	{
	    @PMcmd::Install::MAIN_CHOICE = @{$component_override->{'main-choice'}};
	}

	elsif ( ref $component_data->{'main-choice'} eq 'ARRAY' )
	{
	    @PMcmd::Install::MAIN_CHOICE = @{$component_data->{'main-choice'}};
	}
    }

    return 1;
}


sub OverrideRecursive {
    
    my ($main, $override) = @_;
    
    foreach my $key ( %$override )
    {
	if ( ref $main->{$key} eq 'HASH' && ref $override->{$key} eq 'HASH' )
	{
	    OverrideRecursive($main->{$key}, $override->{$key});
	}

	elsif ( ref $main->{$key} eq 'HASH' )
	{
	    print "WARNING: skipping key '$key' from $CONFIG{local_component_data} because it is not a hashref\n";
	}

	elsif ( ref $main->{$key} eq 'ARRAY' && ref $override->{$key} ne 'ARRAY' )
	{
	    print "WARNING: skipping key '$key' from $CONFIG{local_component_data} because it is not an arrayref\n";
	}
	
	else
	{
	    $main->{$key} = $override->{$key};
	}
    }
}


# ListComponentTemplates ( project_data, relative_name )
#
# Return a list containing the name of each project component for which a file named by
# $relative_name exists in its installed directory, followed by the pathname of that file. This is
# suitable for assigning to a hash.

sub ListComponentTemplates {
    
    my ($relative_name) = @_;
    
    my @result;
    
    foreach my $component ( @INSTALLED_COMPONENTS )
    {
	my $filename = "$COMPONENT{$component}{path}/$relative_name";
	
	if ( -e $filename )
	{
	    push @result, $component, $filename;
	}
    }
    
    return @result;
}


# ReadTemplate ( sections_ref, filename, default_name )
# 
# Read the specified template file. If it exists, store its sections into %$sections_ref. The
# first section in the file is stored under the default name if it does not have a section header
# line.

sub ReadTemplate {
    
    my ($sections_ref, $filename, $default_name) = @_;
    
    # Skip files that don't exist; not every project will have every template.
    
    return unless -e $filename;
    
    # Open the template for reading, or print an error and return false.

    PrintDebug("Reading template file: $filename") if $DEBUG;
    
    my $result = open(my $tf, '<', $filename);
    
    unless ( $result )
    {
	print "\nERROR: could not open $filename: $!\n";
	return;
    }
    
    # Go through the lines of the template, dividing them up into sections.
    
    my $section_name;
    my $temp;
    
 LINE:
    while (my $line = <$tf>)
    {
	# If the next line is a section-start line, then store any pending content.
	
	if ( $line =~ / ^ [#]? \s* [*][*][*] \s+ (\S+)/xs )
	{
	    if ( $temp )
	    {
		my $store_as = $section_name || $default_name;
		$sections_ref->{$store_as} = $temp;
		$temp = [ ];
	    }
	    
	    $section_name = $1;
	}

	elsif ( $line =~ / ^ [#]? \s* [*] /xs )
	{
	    chomp $line;
	    print "\nWARNING: bad section divider '$line'\n";
	    next;
	}
	
	# Otherwise, add it to the buffer of lines pending.
	
	else
	{
	    push @$temp, $line;
	}
    }
    
    # Store any content from the final section, and close the template file.
    
    close $tf;
    
    if ( $temp )
    {
	my $store_as = $section_name || $default_name;
	$sections_ref->{$store_as} = $temp;
    }
    
    return 1;
}


# CheckTemplateTarget ( target_path, ask, @template_paths)
# 
# If the file specified by $target_path is newer than the files specified by the template paths,
# return false. Otherwise, the file may need to be rebuilt. If $ask is true, ask the user whether
# to rebuild the file. If the answer is 'no, return false. Otherwise, return the answer which may
# be either 'yes' or 'quit'.

sub CheckTemplateTarget {

    my ($target_path, $ask, @template_paths) = @_;
    
    my @newer;
    
    foreach my $template ( @template_paths )
    {
	push @newer, $template if -e $template && -M $template < -M $target_path;
    }
    
    if ( @newer )
    {
	if ( $ask )
	{
	    print "\nThe following files are newer than $target_path:\n";
	    print map("    $_\n", @newer);
	    
	    my $answer = AskQuestion(" > Rebuild $target_path? (y/n/q) ", { yesnoquit => 1 });
	    
	    print "\n";
	    return $answer;
	}

	else
	{
	    return 1;
	}
    }
    
    else
    {
	return;
    }
}


# GenerateFileFromTemplate ( target, template, vars, sections )
#
# Put together a file by selecting pieces from a template file. This is used to build the
# Dockerfile and site configuration file for nginx, based on the project pieces included in this
# installation. Return true if the file is newly created or else if the contents have changed.
# If the file already exists and the new contents are the same, leave it alone and return false.

sub GenerateFileFromTemplate {
    
    my ($target_filename, $template, @sections) = @_;
    
    # If the target filename ends in ~, remove that and set $check_only;

    my $check_only;

    if ( $target_filename =~ /^(.*)~$/ )
    {
	$check_only = 1;
	$target_filename = $1;
    }
    
    # # For each element of @sections that is not a hashref, add it to %select with a value of 1.
    
    # Read through the template file. Add the content of each selected section to %section as a
    # list of lines.
    
    my %section;

    # If the second argument is a hash, just copy it into %section.

    if ( ref $template eq 'HASH' )
    {
    	%section = %$template;
    }
    
    # Otherwise, it should be a filename. Open it and read the template sections.

    else
    {
	my %select = map { $_ => 1 } grep { ! ref $_ } @sections;
	
    	open(my $tf, '<', $template) || die "Could not read $template: $!\n";
	
    	my $state = 'START';
    	my $name;
    	my $content = [ ];
	
      LINE:
    	while (my $line = <$tf>)
    	{
    	    # When we come to a new section, save the content of the previous section if it was
    	    # included. If this section is selected, include the lines following it.
	    
    	    if ( $line =~ qr{ ^ (?: \# \s+ )? [*][*][*] \s+ (\S+) (?: \s+ [*][*][*])? }xs )
    	    {
    		if ( $name && @$content )
    		{
    		    $section{$name} = $content;
    		}
		
    		$content = [ ];
		
    		if ( $select{$1} )
    		{
    		    $state = 'INCLUDE';
    		    $name = $1;
    		}
		
    		else
    		{
    		    $state = 'EXCLUDE';
    		    $name = '';
    		}
		
    		next LINE;
    	    }
	    
    	    # Other lines are added to the current section content if the state is 'INCLUDE'.
	    
    	    elsif ( $state eq 'INCLUDE' )
    	    {
    		push @$content, $line;
    	    }
    	}
	
    	# Close out the current section if any, then close the template file.
	
    	if ( $name && @$content )
    	{
    	    $section{$name} = $content;
    	}
	
    	close $tf;
    }
    
    # Then go through the arguments and construct the output.
    
    my $output = '';
    
    # Each scalar value represents a template section to include. It may be followed by a hashref,
    # which gives values to substitute into the template.
    
    my @output_list;
    
    while ( @sections )
    {
	my ($name, $local);
	
	# Grab a section name and optional hash of substitution values.
	
	$name = shift @sections;
	$local = ref $sections[0] eq 'HASH' ? shift @sections : { };
	
	# Check that the section name is one that was defined in the template.
	
	if ( ref $name )
	{
	    print "ERROR: in GenerateFileFromTemplate: extra hashref found\n";
	    next;
	}
	
	unless ( $section{$name} )
	{
	    if ( ref $template )
	    {
		print "ERROR: section '$name' not found in any of the templates\n";
	    }

	    else
	    {
		print "ERROR: section '$name' not found in $template\n";
	    }
	    
	    next;
	}

	# Add this section to the output list, so we can let the user know how the file was
	# generated. If the list of local variable substitutions contains either 'label' or
	# 'domain', include the corresponding value.
	
	if ( my $label = $local->{label} || $local->{domain} )
	{
	    push @output_list, "$name/$label";
	}

	else
	{
	    push @output_list, $name;
	}
	
	# Go through the lines one by one. Substitute any variables; if the value is not found in
	# $local, try the corresponding configuration setting. If that is not defined either,
	# substitute the string 'undefined'.
	
	foreach my $line ( @{$section{$name}} )
	{
	    # If a variable substitution is found, make all substitutions on that line. We use the
	    # 'r' modifier to ensure that the value of $line is not changed, because this template
	    # section might be inserted again later in the output with different substitution values.
	    
	    if ( $line =~ qr| \{\{\w |xs )
	    {
		$output .= $line =~ s| \{\{ (\w+) \}\} | $local->{$1} // $CONFIG{$1} // 'undefined' |egxr;
	    }
	    
	    # Otherwise, just add the line to the output.
	    
	    else
	    {
		$output .= $line;
	    }
	}
    }
    
    # If the newly generated output is empty, throw an exception. This should not ever happen.
    
    unless ( $output )
    {
	die "ERROR: the generated content for $target_filename is empty.\n";
    }
    
    # If the target file already exists, check to see if its contents are the same as what we have
    # just generated. If so, leave it alone and return. If not, rename the old contents to .bak
    
    if ( -e $target_filename )
    {
	if ( open(my $if, '<', $target_filename) )
	{
	    my @input = <$if>;
	    close $if;

	    my $old_content = join('', @input);
	    
	    if ( $old_content eq $output )
	    {
		print "\n - FILE $target_filename is unchanged\n";
		utime undef, undef, $target_filename;
		return;
	    }
	}
	
	else
	{
	    print "WARNING: could not read $target_filename: $!\n";
	}
	
	PrintDebug("rename $target_filename => $target_filename.bak") if $DEBUG;
	rename($target_filename, "$target_filename.bak");
    }
    
    # Write the newly generated output to the target file, or throw an exception if an error
    # occurs.
    
    open(my $of, '>', $target_filename) || die "Could not write $target_filename: $!\n";
    
    print $of $output;
    
    close $of || die "Error closing $target_filename: $!\n";

    # Print a message indicating that we have written the file, and return true because the
    # content has changed.

    my $list = join(', ', @output_list);

    if ( ref $template )
    {
	print "\n - FILE $target_filename generated from templates ($list)\n";
    }

    else
    {
	print "\n - FILE $target_filename generated from $template ($list)\n";
    }
    
    # print @output_list;
    # print "\n";
    
    return 1;
}


# GenerateYAMLFromTemplate ( target, template, subst, sections... )
# 
# Generate the content of the target file using the specified template file and a list of sections
# to choose from that template. The existing content of the target will be overwritten.
# 
# Each template section is initiated by a line that looks like '*** sectionname' or '# *** sectionname'.
# 
# The template contents are assumed to be fragments of YAML, and each piece is integrated into the
# most closely matching piece from the content already generated. So, for example, suppose that a
# selected template section includes the following.
#
# services:
#   nginx:
#     volumes:
#       - type: volume
#         source: ./taxa_downloads
#         target: /var/paleomacro/classic/public/taxa_downloads
# 
# If the content that has already been generated includes a 'services' key with 'nginx' as a
# subkey and 'volumes' as a subkey of that, and the whitespace at the front of each line matches
# up properly, then the remainder of this fragment will be added underneath that 'volumes'
# line. If no 'volumes' subkey is found, then it plus the remainder of the fragment will be added
# under 'nginx'. If no 'nginx' subkey is found, then it plus the remainder of the fragment will be
# added under 'services'. And so on.
#
# If $subst is a hash reference, then substitute instances of {{xxx}} with the corresponding hash
# value, or else with the value of the xxx configuration setting, or the string 'undefined' if no
# defined value is found.

sub GenerateYAMLFromTemplate {
    
    my ($target_filename, $template, $subst, @sections) = @_;
    
    # If the target filename ends in ~, remove that and set $check_only;

    my $check_only;

    if ( $target_filename =~ /^(.*)~$/ )
    {
	$check_only = 1;
	$target_filename = $1;
    }
    
 #    # Create a hash of section names to include.
    
 #    my %select = map { $_ => 1 } @sections;
    
 #    # The @output list consists of those lines that have been fully processed and are ready to be
 #    # written out. When the entire template has been read, the content of this list will be
 #    # written to the target file.
    
 #    my @output;
    
 #    # The @temp list holds pending content that has been read from the template but not yet been
 #    # processed. Whenever a new section or top-level YAML key is reached, the content of this list
 #    # will be integrated with the already generated output.
    
 #    my @temp;

 #    # The @included list keeps track of which sections were used to generate this content.

 #    my @included;
    
 #    # Open the template for reading, or throw an exception.
    
 #    open(my $tf, '<', $template_filename) || die "Could not read $template_filename: $!\n";
    
 #    # Go through the lines of the template, using a simple finite-state machine with start state
 #    # 'START'.
    
 #    my $state = 'START';
    
 # LINE:
 #    while (my $line = <$tf>)
 #    {
 # 	# If the next line is a section-start line, then integrate any pending content from the
 # 	# previous section into the output. If this new section is included, set the state to
 # 	# 'INCLUDE'. Otherwise, set it to 'EXCLUDE'.
	
 # 	if ( $line =~ / ^ [#]? \s* [*][*][*] \s+ (\S+)/xs )
 # 	{
 # 	    IntegrateYAMLSection(\@output, \@temp) if @temp;
 # 	    @temp = ();
	    
 # 	    if ( $select{$1} )
 # 	    {
 # 		$state = 'INCLUDE';
 # 		push @included, $1;
 # 		next LINE;
 # 	    }
	    
 # 	    else
 # 	    {
 # 		$state = 'EXCLUDE';
 # 		next LINE;
 # 	    }
 # 	}

 # 	# Otherwise, if this is a line from an included section then process it. All other lines
 # 	# are ignored.
	
 # 	elsif ( $state eq 'INCLUDE' )
 # 	{
 # 	    # If the line starts with a word followed by a colon, without any initial whitespace,
 # 	    # it represents a new top-level YAML key. Integrate any pending content into the
 # 	    # output, and then reset the pending content list to be just this line.
	    
 # 	    if ( $line =~ / ^ \w+ : $ /xs )
 # 	    {
 # 		IntegrateYAMLSection(\@output, \@temp) if @temp;
 # 		@temp = ($line);
 # 	    }
	    
 # 	    # Otherwise, add this line to the pending content list.
	    
 # 	    else
 # 	    {
 # 		push @temp, $line;
 # 	    }
 # 	}
 #    }
    
 #    # Integrate any remaining content from the last included section, and then close the template
 #    # file.
    
 #    IntegrateYAMLSection(\@output, \@temp) if @temp;
    
 #    close $tf;
    
    # Start with an empty output list. Go through the sections in order and substitute them in.

    my @output;
    my @included;
    my %failed;
    
    foreach my $section_name ( @sections )
    {
	my $content = $template->{$section_name};
	
	if ( $content )
	{
	    push @included, $section_name;
	    my @section_content;
	    
	    foreach my $line ( @$content )
	    {
		if ( $line =~ qr{ ^ \w+ : $ }xs && @section_content )
		{
		    IntegrateYAMLSection(\@output, \@section_content);
		    @section_content = ( $line );
		}
		
		else
		{
		    push @section_content, $line;
		}
	    }

	    if ( @section_content )
	    {
		IntegrateYAMLSection(\@output, \@section_content);
	    }
	}
	
	else
	{
	    $failed{$section_name} = 1;
	}
    }
    
    # If any substitutions were specified, go through @output and perform them.

    if ( ref $subst eq 'HASH' )
    {
	foreach my $line ( @output )
	{
	    if ( $line =~ qr| \{\{\w |xs )
	    {
		$line =~ s| \{\{ (\w+) \}\} | $subst->{$1} // $CONFIG{$1} // 'undefined' |egxs;
	    }
	}
    }
    
    # If the target file already exists, read its contents and check to see if they are the same
    # as what we have just generated. If so, update its modification time and return. Otherwise, rename
    # the old version to .bak
    
    if ( -e $target_filename )
    {
	if ( open(my $if, '<', $target_filename) )
	{
	    my @input = <$if>;
	    close $if;
	    
	    my $difference;
	    
	    foreach my $i ( 0..$#input )
	    {
		$difference = 1 if $input[$i] ne $output[$i];
	    }

	    if ( @input == @output && ! $difference )
	    {
		return if $check_only;
		
		print "\n - FILE $target_filename is unchanged\n";
		utime undef, undef, $target_filename;
		return;
	    }
	}
	
	else
	{
	    print "WARNING: could not read $target_filename: $!\n";
	}
	
	return 1 if $check_only;
	
	PrintDebug("rename $target_filename => $target_filename.bak") if $DEBUG;
	rename($target_filename, "$target_filename.bak");
    }
    
    return 1 if $check_only;
    
    # Write the content of @output to the target file, or throw an exception if an error occurs.
    
    open(my $of, '>', $target_filename) || die "Could not write $target_filename: $!\n";
    
    print $of @output;
    
    close $of || die "Error closing $target_filename: $!\n";
    
    # Read back the content of the target file, and attempt to parse it as YAML. If it does not
    # parse, then print out an error message and restore the old version.
    
    my $check = ReadConfigFile($target_filename, { no_cache => 1 });
    
    unless ( ref $check && reftype($check) eq 'HASH' )
    {
	print "ERROR: the file that was written does not contain valid YAML.\n";
	print "Restoring old version of $target_filename\n";

	PrintDebug("rename $target_filename => $target_filename.bad") if $DEBUG;
	rename($target_filename, "$target_filename.bad");
	PrintDebug("rename $target_filename.bak => $target_filename") if $DEBUG;
	rename("$target_filename.bak", $target_filename);
	return;
    }
    
    # If it does parse, print out a message and return true because the content has changed.
    
    my $sections = join(', ', @included);
    
    print "\n - FILE $target_filename generated from template ($sections)\n";
    return 1;
}


# IntegrateYAMLSection ( output_list, section_list )
#
# Integrate the lines from section_list into output_list, matching YAML keys in section_list to
# YAML keys in output_list whenever possible. When a match is found, subsequent lines from
# section_list are inserted after the matching key's subordinate content until one is reached with
# initial whitespace less than or equal to that of the matching key line.

sub IntegrateYAMLSection {
    
    my ($output_list, $section_list) = @_;

    # print STDOUT "INTEGRATE:\n";
    # print STDOUT @$section_list;
    
    my @search_list;
    my $check_line;
    
    while ( $section_list->[0] =~ qr{ ^ \s* \w+ : \s* $ }xs )
    {
	push @search_list, shift @$section_list;
    }
    
    foreach my $line ( @$section_list )
    {
	next if $line =~ qr{ ^ \s* $ | ^ \s* [#] }xs;
	$check_line = $line if $line =~ qr{ ^ \s* \w+ : $ }xs;
	last;
    }
    
    if ( @search_list )
    {
	pop @$section_list while $section_list->[-1] eq "\n";
    }
    
    my $search_indent = '';
    my $found;
    my $inserted;
    
  LINE:
    for ( my $ln = 0; $ln < @$output_list; $ln++ )
    {
	my $line = $output_list->[$ln];
	$line =~ / ^ ( [ ]* ) /xs;
	my $line_indent = $1;
	
	if ( @search_list && $line eq $search_list[0] )
	{
	    $found = $line;
	    shift @search_list;
	    $search_indent = $line_indent;
	}
	
	elsif ( $found && ! @search_list && $check_line && $line eq $check_line )
	{
	    print "WARNING: skipped duplicate section '$check_line' under '$found'\n";
	    return;
	}
	
	elsif ( $found && length($line_indent) <= length($search_indent) )
	{
	    splice(@$output_list, $ln, 0, @search_list, @$section_list);
	    $inserted = 1;
	    last LINE;
	}
    }
    
    unless ( $inserted )
    {
	push @$output_list, @search_list, @$section_list;
    }
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


