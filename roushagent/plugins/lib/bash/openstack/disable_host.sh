#!/bin/bash
set -o errexit
source "$ROUSH_BASH_DIR/roush.sh"

if [[ ! -e /root/openrc ]]; then
    echo "/root/openrc does not exist and I cannot continue.  Good bye."
    exit 1
fi

if [[ ! -e /usr/bin/nova-manage ]]; then
    echo "nova-manage has not been installed and I cannot continue without it.  Good bye."
    exit 2
fi

. /root/openrc

nova-manage service disable --service=nova-compute --host=$(hostname -f)

return_fact "maintenance_mode" "true"
