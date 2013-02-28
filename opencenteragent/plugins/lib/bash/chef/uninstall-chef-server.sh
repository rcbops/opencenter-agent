#!/bin/bash
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

source "$OPENCENTER_BASH_DIR/opencenter.sh"
set -x
export DEBIAN_FRONTEND=noninteractive

id_OS

chef-server-ctl uninstall
if [[ $OS_TYPE = "debian"  ]] || [[ $OS_TYPE = "ubuntu" ]]; then
    dpkg -P chef-server
    apt-get autoremove purge -y
elif [[ $OS_TYPE = "redhat"  ]] || [[ $OS_TYPE = "centos" ]] || [[ $OS_TYPE = "fedora" ]]; then
    rpm -e chef-server
fi
rm -rf /etc/chef-server /etc/chef /opt/chef-server /opt/chef /root/.chef /var/opt/chef-server/
rm -rf /var/chef /var/log/chef-server/
sed -i  '/export PATH=\${PATH}:\/opt\/chef-server\/bin/d' /root/.profile
pkill -f chef
pkill -f beam
pkill -f postgres
return_consequence "facts.backends := remove(facts.backends, 'chef-server')"
for fact in chef_server_client_name chef_server_client_pem chef_server_uri chef_server_pem chef_server_cookbook_channels; do
    return_fact "${fact}" "none"
done
