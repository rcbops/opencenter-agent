#! /bin/bash

set -e
set -u
set -x

PACKAGE_NAME=${PACKAGE_NAME:-}
RETVAL=0

if [[ -f /etc/redhat-release ]]; then
    DISTRO="redhat"
else
    DISTRO="debian"
fi

export DEBIAN_FRONTEND=noninteractive

function do_single_package() {
    if [[ $DISTRO = "debian" ]]; then
        apt-get -o Dpkg::Options::='--force-confold' -o Dpkg::Options::='--force-confdef' -y install ${PACKAGE_NAME}
        RETVAL=$?
    else
        yum -y install ${PACKAGE_NAME}
        RETVAL=$?
    fi
}

function do_update() {
    if [[ $DISTRO = "debian" ]]; then
        apt-get -o Dpkg::Options::='--force-confold' -o Dpkg::Options::='--force-confdef' -y upgrade
        RETVAL=$?
    else
        yum -y upgrade
        RETVAL=$?
    fi
}

if [[ -z $PACKAGE_NAME ]]; then
	do_update
else
	do_single_package
fi

exit $RETVAL
