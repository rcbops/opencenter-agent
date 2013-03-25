#!/bin/bash
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
#

set -e
set -u
set -x

source "$OPENCENTER_BASH_DIR/opencenter.sh"

DISABLE_RESTART=${DISABLE_RESTART:-}
PACKAGE_NAME=${PACKAGE_NAME:-}
RETVAL=0

id_OS
export DEBIAN_FRONTEND=noninteractive

function do_single_package() {
    if [[ $OS_TYPE = "debian"  ]] || [[ $OS_TYPE = "ubuntu" ]]; then
        dpkg -l ${PACKAGE_NAME} &> /dev/null
        if [[ $? -eq 0 ]]; then
            SKIP=$(echo ${DISABLE_RESTART} | tr '[:upper:]' '[:lower:]')
            if [[ ${SKIP} = "true" ]]; then
                echo -e '#!/bin/sh \nexit 101' > /usr/sbin/policy-rc.d
                chmod +x /usr/sbin/policy-rc.d
            fi
            apt-get -o Dpkg::Options::='--force-confold' -o Dpkg::Options::='--force-confdef' -y install ${PACKAGE_NAME}
            RETVAL=$?
            if [[ -e /usr/sbin/policy-rc.d ]]; then
                rm /usr/sbin/policy-rc.d
            fi
        else
            RETVAL=1
        fi
    else
        rpm -q ${PACKAGE_NAME} &> /dev/null
        if [[ $? -eq 0 ]]; then
            yum -y install ${PACKAGE_NAME}
            RETVAL=$?
        else
            RETVAL=1
        fi
    fi

    return $RETVAL
}

function do_update() {
    if [[ $OS_TYPE = "debian"  ]] || [[ $OS_TYPE = "ubuntu" ]]; then
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
