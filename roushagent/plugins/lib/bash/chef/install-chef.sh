#!/bin/bash

set -o errexit
source "$ROUSH_BASH_DIR/roush.sh"

# forcing chef-client install to 10.18.2-2
CHEF_CLIENT_VERSION=${CHEF_CLIENT_VERSION:-"10.18.2-2"}

if [[ -f /etc/redhat-release ]]; then
    DISTRO="redhat"
else
    DISTRO="debian"
fi

REQUIRED="CHEF_SERVER_URL CHEF_SERVER_PEM CHEF_SERVER_HOSTNAME"
for r in $REQUIRED; do
    if [[ -z ${!r} ]]; then
        echo Environment variable $r required but not set 1>&2
        exit 22
    fi
done

# pad the /etc/hosts file, as chef 11 seems to somehow require name resolution
CHEF_HOST_PARTS=(${CHEF_SERVER_HOSTNAME//./ })
CHEF_SERVER_SHORTNAME=${CHEF_HOST_PARTS[0]}
CHEF_SERVER_IP=$(echo ${CHEF_SERVER_URL} | sed -e 's#.*://\([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+\).*#\1#')

if ( ! grep -q "${CHEF_SERVER_SHORTNAME}" /etc/hosts ); then
    echo -e "\n${CHEF_SERVER_IP}\t${CHEF_SERVER_SHORTNAME}\t${CHEF_SERVER_HOSTNAME}\n" >> /etc/hosts
fi

CHEF_ENVIRONMENT=${CHEF_ENVIRONMENT:-_default}
DEBIAN_FRONTEND=noninteractive apt-get install curl -y --force-yes
curl -skS -L http://www.opscode.com/chef/install.sh | bash -s - -v ${CHEF_CLIENT_VERSION}
if ! [[ -e /etc/chef ]]; then
    mkdir -p /etc/chef
fi
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

CHEF_CLIENT_VERSION=$(chef-client --version | awk -F": " '{print $2}')
if [[ $DISTRO = "debian" ]]; then
    cp /opt/chef/embedded/lib/ruby/gems/1.9.[0-9]/gems/chef-${CHEF_CLIENT_VERSION}/distro/debian/etc/default/chef-client /etc/default/chef-client
    cp /opt/chef/embedded/lib/ruby/gems/1.9.[0-9]/gems/chef-${CHEF_CLIENT_VERSION}/distro/debian/etc/init.d/chef-client /etc/init.d/chef-client
elif [[ $DISTRO = "redhat" ]]; then
    cp /opt/chef/embedded/./lib/ruby/gems/1.9.[0-9]/gems/chef-${CHEF_CLIENT_VERSION}/distro/redhat/etc/init.d/chef-client /etc/init.d/chef-client
    chkconfig --add /etc/init.d/chef-client
    chkconfig chef-client on
fi

chmod +rx /etc/init.d/chef-client
mkdir -p /var/log/chef

chef-client
chef-client

# /etc/init.d/chef-client start

return_attr "chef_client_version" "'${CHEF_CLIENT_VERSION}'"
