#!/bin/bash

source "$ROUSH_BASH_DIR/roush.sh"

dpkg -P chef
rm -rf /etc/chef
if ! [[ -e /opt ]]; then
    mkdir -p /opt
fi

return_consequence "facts.backends := remove(facts.backends, 'chef-client')"
