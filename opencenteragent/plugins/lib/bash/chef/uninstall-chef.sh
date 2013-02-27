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

if [ -f /etc/chef/knife.rb ]; then
    knife node delete `hostname` -y -c /etc/chef/knife.rb || :
    knife client delete `hostname` -y -c /etc/chef/knife.rb || :
fi

dpkg -P chef
rm -rf /etc/chef
if ! [[ -e /opt ]]; then
    mkdir -p /opt
fi

return_consequence "facts.backends := remove(facts.backends, 'chef-client')"
return_attr "chef_client_version" "none"
for fact in chef_environment chef_server_consumed; do
    return_fact "${fact}" "none"
done
