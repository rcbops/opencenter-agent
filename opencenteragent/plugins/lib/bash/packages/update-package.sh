#! /bin/bash
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
