#!/bin/bash

set -o errexit
source "$ROUSH_BASH_DIR/roush.sh"

if [[ -f /etc/redhat-release ]]; then
    DISTRO="redhat"
else
    DISTRO="debian"
fi

REQUIRED="CHEF_SERVER CHEF_VALIDATOR"
for r in $REQUIRED; do
    if [[ -z ${!r} ]]; then
        echo Environment variable $r required but not set 1>&2
        exit 22
    fi
done

CHEF_ENVIRONMENT=${CHEF_ENVIRONMENT:-_default}
DEBIAN_FRONTEND=noninteractive apt-get install curl -y --force-yes
curl -skS -L http://www.opscode.com/chef/install.sh | bash
mkdir -p /etc/chef
cat <<EOF >/etc/chef/client.rb
chef_server_url "$CHEF_SERVER_URL"
chef_environment "$CHEF_ENVIRONMENT"
EOF
if [ -n "${CHEF_VALIDATION_NAME}" ]; then
    echo "validation_client_name '$CHEF_VALIDATION_NAME'" >> /etc/chef/client.rb
fi

cat <<EOF > /etc/chef/validation.pem
$CHEF_SERVER_PEM
EOF

if [[ $DISTRO = "debian" ]]; then
    cp /opt/chef/embedded/lib/ruby/gems/1.9.[0-9]/gems/chef-10.1[2-4].[0-9]/distro/debian/etc/default/chef-client /etc/default/chef-client
    cp /opt/chef/embedded/lib/ruby/gems/1.9.[0-9]/gems/chef-10.1[2-4].[0-9]/distro/debian/etc/init.d/chef-client /etc/init.d/chef-client
elif [[ $DISTRO = "redhat" ]]; then
    cp /opt/chef/embedded/./lib/ruby/gems/1.9.1/gems/chef-10.12.0.rc.1/distro/redhat/etc/init.d/chef-client /etc/init.d/chef-client
    chkconfig --add /etc/init.d/chef-client
    chkconfig chef-client on
fi

return_fact "chef_server_uri" "$CHEF_SERVER"
return_fact "chef_server_pem" "$CHEF_VALIDATOR"

chmod +rx /etc/init.d/chef-client
mkdir -p /var/log/chef
/etc/init.d/chef-client start
