# cloudserver_base

This repository contains the base directory tree for the dockerized version of the paleobiodb. It includes the source code for the installation script 'install.pl' and the control/status command 'pbdb'. It also contains templates for the main configuration files.

# Changes on November 15, 2021 (Daven Quinn)

Needed to reclaim space on server to re-initialize LVM
- Deleted `volumes` directory including contents of database clusters
- Moved to another location for potential reintegration later