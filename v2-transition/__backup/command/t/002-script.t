#
#


use lib 'lib';

use Test::More tests => 1;


my $check;

eval {
    $check = `perl script/pbdb version`
};

ok($check);



