#! /bin/bash

set -e
set -u
set -x

destdir=${CHEF_REPO_DIR:-/root/chef-cookbooks}
url=${CHEF_CURRENT_COOKBOOK_URL}
md5=${CHEF_CURRENT_COOKBOOK_MD5}
version=${CHEF_CURRENT_COOKBOOK_VERSION}
#repo=${CHEF_REPO:-https://github.com/rcbops/chef-cookbooks}
#branch=${CHEF_REPO_BRANCH:-master}
knife_file=${CHEF_KNIFE_FILE:-/root/.chef/knife.rb}

# Include the cookbook-functions.sh file
source $OPENCENTER_BASH_DIR/chef/cookbook-functions.sh

# Include the opencenter functions
source $OPENCENTER_BASH_DIR/opencenter.sh

get_prereqs
#checkout_master "${destdir}" "${repo}" "${branch}"
download_cookbooks "${destdir}" "${version}" "${url}" "${md5}"
update_submodules "${destdir}"
upload_cookbooks "${destdir}" "${knife_file}"
upload_roles "${destdir}" "${knife_file}"

return_fact "chef_server_cookbook_version" "'${version}'"

