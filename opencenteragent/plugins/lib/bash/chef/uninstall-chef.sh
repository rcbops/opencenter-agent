#!/bin/bash

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
