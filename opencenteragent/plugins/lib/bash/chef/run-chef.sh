#!/bin/bash

source "$OPENCENTER_BASH_DIR/opencenter.sh"

if (! chef-client ); then
    chef-client
fi

if [ $? -eq 0 ]; then
    return_consequence "attrs.converged := true"
else
    return_consequence "attrs.converged := false"
fi
