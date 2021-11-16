# Before 'make install' is performed this script should be runnable with
# 'make test'. After 'make install' it should work as 'perl 001-module.t'

#########################

# change 'tests => 1' to 'tests => last_test_to_print';

use strict;
use warnings;

use lib 'lib';

use Test::More tests => 7;
BEGIN {
    use_ok('PMCmd::Config');
    use_ok('PMCmd::System');
    use_ok('PMCmd::Command');
    use_ok('PMCmd::Build');
    # use_ok('PMCmd::Backup');
    use_ok('PMCmd::Install');
    use_ok('PMCmd::DBVersion');
    use_ok('PMCmd::PBTasks');
};




#########################

# Insert your test code below, the Test::More module is use()ed here so read
# its man page ( perldoc Test::More ) for help writing this test script.

