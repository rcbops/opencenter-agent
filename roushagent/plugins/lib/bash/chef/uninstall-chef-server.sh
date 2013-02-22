#!/bin/bash

source "$ROUSH_BASH_DIR/roush.sh"
set -x

chef-server-ctl uninstall
dpkg -P chef-server
rm -rf /etc/chef-server /etc/chef /opt/chef-server /opt/chef /root/.chef /var/opt/chef-server/
rm -rf /var/chef /var/log/chef-server/
sed -i  '/export PATH=\${PATH}:\/opt\/chef-server\/bin/d' /root/.profile

return_consequence "facts.backends := remove(facts.backends, 'chef-server')"
for fact in chef_server_client_name chef_server_client_pem chef_server_uri chef_server_pem chef_server_cookbook_channels; do
    return_fact "${fact}" "none"
done
