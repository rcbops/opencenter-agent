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

set -o errexit
source "$OPENCENTER_BASH_DIR/opencenter.sh"

apt-get -y install bc

# wait up to x seconds from the start of the migration to the second try
WAIT_FOR_BUILD_TIMEOUT=300
WAIT_FOR_MIGRATION_TIMEOUT=600

echo ""

if [ ! -e /etc/nova/nova.conf ]; then
    echo "/etc/nova/nova.conf does not exist.  We cannot continue"
    return_fact "maintenance_mode" "'failed'"
    exit 1
fi

if [ ! -e /usr/bin/nova-manage ]; then
    echo "nova-manage does not exist.  We cannot continue"
    return_fact "maintenance_mode" "'failed'"
    exit 2
fi

if [ ! -e /usr/bin/nova ]; then
    echo "nova does not exist.  We cannot continue"
    exit 3
fi

if [ ! -e /root/openrc ]; then
    echo "/root/openrc does not exist.  We cannot continue"
    return_fact "maintenance_mode" "'failed'"
    exit 4
fi

. /root/openrc

CURRENT_AZ=$(grep node_availability_zone /etc/nova/nova.conf | awk -F "=" '{print $2}')
echo "Current AZ"
echo "----------"
echo ${CURRENT_AZ}
echo ""

AZ_HOSTS=$(nova-manage service list --service nova-compute | sort -R | awk '{if($3=="'${CURRENT_AZ}'" && $4=="enabled" && $5==":-)") print $2}')
AZ_HOSTS_ARRAY=(${AZ_HOSTS// / })
echo "Hosts available for Migration"
echo "-----------------------------"
echo ${AZ_HOSTS}
echo ""

echo "# of Hosts available in AZ ${CURRENT_AZ}"
echo "----------------------------------------"
echo ${#AZ_HOSTS_ARRAY[@]}
echo ""

if [[ ${#AZ_HOSTS_ARRAY[@]} = 0 ]]; then
    echo "!! There are no hosts available to migrate instances to"
    return_fact "maintenance_mode" "'failed'"
    exit 5
fi

echo "-- disabling nova-compute service on "$(hostname -f)
nova-manage service disable --service=nova-compute --host=$(hostname -f)


for (( try_migrate=0; try_migrate < 5; try_migrate++ )) do
    sleep_timer=$((60 - ( 12 * try_migrate ) ))
    echo "-- sleeping for $sleep_timer seconds"
    sleep $sleep_timer
    echo ""

    echo "-- migrate loop ${try_migrate}"
    MIGRATE_INSTANCES=$(nova list --host $(hostname -f) --all-tenants 1 | awk '{if(length($1)==1 && $2!="ID") print $2","$6}')

    for host in ${MIGRATE_INSTANCES}; do
        hostinfo=(${host//,/ })
        UUID=${hostinfo[0]}
        STATUS=${hostinfo[1]}
        if [[ "${STATUS}" = "ACTIVE" ]]; then
            echo "-- Starting migration for ${UUID}"
            for migrate_host in ${AZ_HOSTS_ARRAY[@]}; do
                echo "---- checking resource allocation on ${migrate_host}"
                HOST_TOTAL_VCPU=$(nova-manage service describe_resource --host ${migrate_host} | grep "(total)" | awk '{print $2}')
                HOST_TOTAL_MEM=$(nova-manage service describe_resource --host ${migrate_host} | grep "(total)" | awk '{print $3}')
                HOST_TOTAL_DISK=$(nova-manage service describe_resource --host ${migrate_host} | grep "(total)" | awk '{print $4}')

                HOST_CUR_VCPU=$(nova-manage service describe_resource --host ${migrate_host} | grep "(used_now)" | awk '{print $2}')
                HOST_CUR_MEM=$(nova-manage service describe_resource --host ${migrate_host} | grep "(used_now)" | awk '{print $3}')
                HOST_CUR_DISK=$(nova-manage service describe_resource --host ${migrate_host} | grep "(used_now)" | awk '{print $4}')

                VCPU_ALLOCATION_RATIO=$(grep ^cpu_allocation_ratio /etc/nova/nova.conf | awk -F "=" '{print $2}')
                # commented  out until the over_allocation bug is fixed
                #RAM_ALLOCATION_RATIO=$(grep ^ram_allocation_ratio /etc/nova/nova.conf | awk -F "=" '{print $2}')
                RAM_ALLOCATION_RATIO=1

                INSTANCE_FLAVOR_NAME=$(nova show ${UUID} | awk '/flavor/ {print $4}')
                FLAVOR_VCPU=$(nova flavor-show ${INSTANCE_FLAVOR_NAME} | awk '/vcpus/ {print $4}')
                FLAVOR_MEM=$(nova flavor-show ${INSTANCE_FLAVOR_NAME} | awk '/ram/ {print $4}')
                FLAVOR_DISK=$(nova flavor-show ${INSTANCE_FLAVOR_NAME} | awk '/disk/ {print $4}')

                TEST_MEM=$(echo "${HOST_TOTAL_MEM} * ${RAM_ALLOCATION_RATIO}" | bc | awk -F "." '{print $1}')
                TEST_VCPU=$(echo "${HOST_TOTAL_VCPU} * ${VCPU_ALLOCATION_RATIO}" | bc | awk -F "." '{print $1}')

                echo "---- ${migrate_host}: $FLAVOR_MEM + $HOST_CUR_MEM > $TEST_MEM"
                echo "---- ${migrate_host}: $FLAVOR_VCPU + $HOST_CUR_VCPU > $TEST_VCPU "
                echo "---- ${migrate_host}: $FLAVOR_DISK + $HOST_CUR_DISK > $HOST_TOTAL_DISK"
                if (( FLAVOR_MEM + HOST_CUR_MEM > TEST_MEM )) ||
                   (( FLAVOR_VCPU + HOST_CUR_VCPU > TEST_VCPU )) ||
                   (( FLAVOR_DISK + HOST_CUR_DISK > HOST_TOTAL_DISK )); then
                    echo "SKIPPING ${migrate_host}... not enough resources"

                else
                    echo "---- trying to migrate to ${migrate_host}"
                    nova live-migration --block-migrate ${UUID} ${migrate_host}
                    count=0
                                while [ "ACTIVE" != "$(nova show ${UUID} | grep status | awk '{print $4}')" ] && (( count < WAIT_FOR_MIGRATION_TIMEOUT / 10 )); do
                        echo "---- waiting for ${UUID} to become active"
                        sleep 10
                        count=$((count + 1))
                    done
                    if [[ ${count} -eq $((WAIT_FOR_MIGRATION_TIMEOUT / 10)) ]]; then
                        echo "!! We hit the timeout and the instance did not got active.  Resetting the state back to active"
                        nova reset-state --active ${UUID}
                        break
                    fi
                    MIGRATION_LANDING_HOST=$(nova show ${UUID} | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}')
                    if [[ "${MIGRATION_LANDING_HOST}" = "${migrate_host}" ]]; then
                        echo "---- MIGRATION was successful.  Instance ${UUID} was moved from $(hostname -f) to ${MIGRATION_LANDING_HOST}"
                            break
                    else
                        echo "!! The migration FAILED.  Trying again."
                    fi
                fi
            done
            echo ""
        else
            echo "-- Skipping migration of ${UUID} because it is in status ${STATUS}"
        fi
    done
done

# see if anything remains
MIGRATE_INSTANCES=$(nova list --host $(hostname -f) --all-tenants 1 | awk '{if(length($1)==1 && $2!="ID") print $2","$6}')
if [[ ${#MIGRATE_INSTANCES[@]} -gt 1 ]]; then
    echo "There are still hosts remaining on the box and we have entered the DANGER ZONE.  We need MANUAL INTERVENTION"
    return_fact "maintenance_mode" "'failed'"
    exit 6
else
    echo "There are no more instances remaining on the box.  SUCCESS IS MINE!"
fi

return_fact "maintenance_mode" "true"
