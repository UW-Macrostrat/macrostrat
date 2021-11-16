use 5.014001;
use ExtUtils::MakeMaker;
# See lib/ExtUtils/MakeMaker.pm for details of how to influence
# the contents of the Makefile that is written.
WriteMakefile(
    NAME              => 'pbdb',
    VERSION_FROM      => 'lib/PMCmd/Config.pm', # finds $VERSION, requires EU::MM from perl >= 5.5
    EXE_FILES         => [ 'script/pbdb', 'script/macrostrat' ],
    PREREQ_PM         => { 'YAML::Tiny' => 1.0 }, # e.g., Module::Name => 1.1
    ABSTRACT          => 'control script for dockerized Paleobiology Database server',
    AUTHOR            => 'Michael McClennen <mmcclenn@geology.wisc.edu>',
    LICENSE           => 'perl',
);

