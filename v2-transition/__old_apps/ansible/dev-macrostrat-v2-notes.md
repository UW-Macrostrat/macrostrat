# Early 2023

Setting up a new development server for Macrostrat:

Created user daven

# Ansible commands

# https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-ansible-on-ubuntu-20-04

Instead of using ansible hosts at `/etc/ansible/hosts`, we define a file in this directory:

ansible-inventory -i "$(pwd)/hosts" --list -y

`run-ansible` command created to always use `hosts` file here.

`run-ansible all -v -m ping`

# Notes on ansible

We can run commands entirely on remote hosts, if we want.
This can be advantageous to do things like copying databases easily.
https://stackoverflow.com/questions/18900236/run-command-on-the-ansible-host