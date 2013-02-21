#!/bin/bash
set -o errexit
source "$ROUSH_BASH_DIR/roush.sh"

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
    exit 1
fi

if [ ! -e /usr/bin/nova ]; then
    echo "nova does not exist.  We cannot continue"
    exit 1
fi

CURRENT_AZ=$(grep node_availability_zone /etc/nova/nova.conf | awk -F "=" '{print $2}')
echo "Current AZ"
echo "----------"
echo ${CURRENT_AZ}
echo ""

AZ_HOSTS=$(nova-manage service list --service nova-compute | sort -R | awk '{if($3=="'${CURRENT_AZ}'" && $4=="enabled" && $5==":-)") print $2}')
echo "Hosts available for Migration"
echo "-----------------------------"
echo ${AZ_HOSTS}
echo ""

echo "# of Hosts available in AZ ${CURRENT_AZ}"
echo "----------------------------------------"
echo ${#AZ_HOSTS[@]}
echo ""

if [[ ${#AZ_HOSTS[@]} = 0 ]]; then
    echo "!! There are no hosts available to migrate instances to"
    return_fact "maintenance_mode" "'failed'"
    exit 2
fi

echo "-- disabling nova-compute service on "$(hostname -f)
nova-manage service disable --service=nova-compute --host=$(hostname -f)


for (( try_migrate=1; try_migrate <= 5; try_migrate++ )) do
    echo "-- sleeping for 60 seconds"
    sleep 60s
    echo ""

    echo "-- migrate loop ${try_migrate}"
    MIGRATE_INSTANCES=$(nova list --host $(hostname -f) --all-tenants 1 | awk '{if(length($1)==1 && $2!="ID") print $2","$6}')

    for host in ${MIGRATE_INSTANCES}; do
            hostinfo=(${host//,/ })
        UUID=${hostinfo[0]}
        STATUS=${hostinfo[1]}
        if [[ "${STATUS}" = "ACTIVE" ]]; then
            echo "-- Starting migration for ${UUID}"
            for migrate_host in ${AZ_HOSTS}; do
                echo "---- trying to migrate to ${migrate_host}"
                nova live-migration --block-migrate ${UUID} ${migrate_host}
                count=0
                            while [ "ACTIVE" != "$(nova show ${UUID} | grep status | awk '{print $4}')" ] && (( count < WAIT_FOR_MIGRATION_TIMEOUT / 10 )); do
                    echo "---- waiting for ${UUID} to become active"
                    sleep 10
                    count=$((count + 1))
                done
                echo "count=${count}"
                if [[ ${count} -eq $((WAIT_FOR_MIGRATION_TIMEOUT / 10)) ]]; then
                    echo "!! We hit the timeout and the instance did not got active."
                    break
                fi
                MIGRATION_LANDING_HOST=$(nova show ${UUID} | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}')
                if [[ "${MIGRATION_LANDING_HOST}" = "${migrate_host}" ]]; then
                    echo "---- MIGRATION was successful.  Instance ${UUID} was moved from $(hostname -f) to ${MIGRATION_LANDING_HOST}"
                        break
                else
                    echo "!! The migration FAILED.  Trying again."
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
if [[ ${#MIGRATE_INSTANCES[@]} -gt 0 ]]; then
    echo "There are still hosts remaining on the box and we have entered the DANGER ZONE.  We need MANUAL INTERVENTION"
    return_fact "maintenance_mode" "'failed'"
    exit 3
else
    echo "There are no more instances remaining on the box.  SUCCESS IS MINE!"
fi

return_fact "maintenance_mode" "true"
