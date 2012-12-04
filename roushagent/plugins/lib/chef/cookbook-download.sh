#! /bin/bash

set -e
set -u
set -x

destdir=${CHEF_REPO_DIR:-/root/chef-cookbooks}
repo=${CHEF_REPO:-https://github.com/rcbops/chef-cookbooks}
branch=${CHEF_REPO_BRANCH:-master}
knife_file=${CHEF_KNIFE_FILE:-/root/.chef/knife.rb}

# Include the cookbook-functions.sh file
source cookbook-functions.sh

get_prereqs
checkout_master "${destdir}" "${repo}" "${branch}"
update_submodules "${destdir}"
upload_cookbooks "${destdir}" "${knife_file}"
upload_roles "${destdir}" "${knife_file}"
