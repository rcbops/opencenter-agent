#!/bin/bash
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

source "$OPENCENTER_BASH_DIR/opencenter.sh"
set -x
export DEBIAN_FRONTEND=noninteractive

chef-server-ctl uninstall
dpkg -P chef-server
rm -rf /etc/chef-server /etc/chef /opt/chef-server /opt/chef /root/.chef /var/opt/chef-server/
rm -rf /var/chef /var/log/chef-server/
sed -i  '/export PATH=\${PATH}:\/opt\/chef-server\/bin/d' /root/.profile
apt-get autoremove purge -y
pkill -f chef
pkill -f beam
pkill -f postgres
return_consequence "facts.backends := remove(facts.backends, 'chef-server')"
for fact in chef_server_client_name chef_server_client_pem chef_server_uri chef_server_pem chef_server_cookbook_channels; do
    return_fact "${fact}" "none"
done
