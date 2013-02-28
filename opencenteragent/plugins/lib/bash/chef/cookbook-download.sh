#! /bin/bash
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
#

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

