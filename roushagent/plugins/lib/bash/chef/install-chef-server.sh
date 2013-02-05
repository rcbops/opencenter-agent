#! /bin/bash
#Flagrantly stolen from rpedde (http://www.github.com/rpedde)

set -e
set -u
export DEBIAN_FRONTEND=noninteractive
source "$ROUSH_BASH_DIR/roush.sh"

if ! [[ -e /etc/debian_version ]] ; then
    echo "Attempted to run debian derivative script on non-debian distribution" 1>&2
    exit 1
fi

function get_sel() {
    # $1 - debconf selection to get

    local value=""
    if ( debconf-get-selections | grep -q ${1}); then
        value=$(debconf-get-selections | grep ${1} | awk '{ print $4 }')
        echo "Found existing debconf value for ${1}: ${value}" >&2
    fi

    echo ${value}
}

locale-gen en_US.UTF-8

apt-get install -y --force-yes debconf-utils pwgen wget lsb-release
cp /etc/resolv.conf /tmp/rc
apt-get remove --purge resolvconf -y --force-yes
cp /tmp/rc /etc/resolv.conf

PRIMARY_INTERFACE=$(ip route list match 0.0.0.0 | awk 'NR==1 {print $5}')
MY_IP=$(ip addr show dev ${PRIMARY_INTERFACE} | awk 'NR==3 {print $2}' | cut -d '/' -f1)

CHEF_URL=${CHEF_URL:-$(get_sel "chef/chef_server_url")}
CHEF_AMQP_PASSWORD=${CHEF_AMQP_PASSWORD:-$(get_sel "chef-solr/amqp_password")}
#CHEF_WEBUI_PASSWORD=${CHEF_WEBUI_PASSWORD:-$(get_sel "chef-server-webui/admin_password")}
CHEF_UNIX_USER=${CHEF_UNIX_USER:-root}

# defaults if not set
CHEF_URL=${CHEF_URL:-https://${MY_IP}}
CHEF_AMQP_PASSWORD=${CHEF_AMQP_PASSWORD:-$(pwgen -1)}
#CHEF_WEBUI_PASSWORD=${CHEF_WEBUI_PASSWORD:-$(pwgen -1)}

cat <<EOF | debconf-set-selections
chef chef/chef_server_url string ${CHEF_URL}
chef-solr chef-solr/amqp_password password ${CHEF_AMQP_PASSWORD}
#chef-server-webui chef-server-webui/admin_password password ${CHEF_WEBUI_PASSWORD}
EOF

if ! dpkg -l chef-server | grep -v '^ii ' &>/dev/null; then
    curl https://opscode-omnitruck-release.s3.amazonaws.com/ubuntu/12.04/x86_64/chef-server_11.0.4-1.ubuntu.12.04_amd64.deb > /tmp/chef-server.deb
    dpkg -i /tmp/chef-server.deb
    chef-server-ctl reconfigure
    rm -f /tmp/chef-server.deb
fi

# is this needed?
#if ! dpkg -l chef-client | grep -v '^ii ' &>/dev/null; then
#    curl -skS -L http://www.opscode.com/chef/install.sh | bash -s - -v 10.18.2-2
#fi

HOMEDIR=$(getent passwd ${CHEF_UNIX_USER} | cut -d: -f6)
mkdir -p ${HOMEDIR}/.chef
cp /etc/chef-server/{chef-validator.pem,chef-webui.pem,admin.pem} ${HOMEDIR}/.chef
chown -R ${CHEF_UNIX_USER}: ${HOMEDIR}/.chef

sleep 10

if [[ ! -e ${HOMEDIR}/.chef/knife.rb ]]; then
cat <<EOF | /opt/chef-server/bin/knife configure -i
${HOMEDIR}/.chef/knife.rb
${CHEF_URL}
admin
chef-webui
${HOMEDIR}/.chef/chef-webui.pem
chef-validator
${HOMEDIR}/.chef/chef-validator.pem

EOF
fi

# setup the path
echo 'export PATH=${PATH}:/opt/chef-server/bin' >> ${HOMEDIR}/.profile

return_fact "chef_server_client_name" "'admin'"
return_fact "chef_server_client_pem" "'$(cat /root/.chef/admin.pem)'"
return_fact "chef_server_uri" "'$CHEF_URL'"
return_fact "chef_server_pem" "'$(cat /etc/chef/validation.pem)'"
#return_attr "chef_webui_password" "'$CHEF_WEBUI_PASSWORD'"
return_attr "chef_webui_password" "'p@ssw0rd1'"
