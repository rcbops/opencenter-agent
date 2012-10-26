#!/bin/bash

dpkg -P chef
rm -rf /etc/chef
if ! [[ -e /opt ]]; then
    mkdir -p /opt
fi
