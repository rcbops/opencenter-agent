#!/bin/bash

REQUIRED="CHEF_SERVER CHEF_VALIDATOR"
for r in required; do
    if [[ -z ${!r} ]]; then
        exit 1
    fi
done
CHEF_ENVIRONMENT=${CHEF_ENVIRONMENT:-_default}
DEBIAN_FRONTEND=noninteractive apt-get install curl -y --force-yes
curl -skS https://raw.github.com/opscode/omnibus/master/source/install.sh | bash
mkdir -p /etc/chef
cat <<EOF >/etc/chef/client.rb
chef_server_url "$CHEF_SERVER"
chef_environment "$CHEF_ENVIRONMENT"
EOF
if [ -n "${VALIDATION_NAME}" ]; then
    echo "validation_client_name '$VALIDATION_NAME'" >> /etc/chef/client.rb
fi

cat <<EOF > /etc/chef/validation.pem
$CHEF_VALIDATOR
EOF
cp /opt/chef/embedded/lib/ruby/gems/1.9.1/gems/chef-10.12.0/distro/debian/e
tc/default/chef-client /etc/default/chef-client
cp /opt/chef/embedded/lib/ruby/gems/1.9.1/gems/chef-10.12.0/distro/debian/etc/init.d/chef-client /etc/init.d/chef-client
mkdir -p /var/log/chef
/etc/init.d/chef-client start
