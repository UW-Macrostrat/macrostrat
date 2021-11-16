#
# Paleobiology Database installation and update command
# 
# This module makes the definitions necessary for the setup and maintenance of an installation.
# 
# Author: Michael McClennen
# Created: 2019-12-13


use strict;

package PMCmd::Setup;

use parent 'Exporter';

use PMCmd::Config qw($MAIN_PATH $PROJECT_DATA ReadConfigFile);

our (@EXPORT_OK) = qw(@CONF_FILE %CONF_FILE %CONF_REBUILD @SQL_FILES ReadProjectData);


