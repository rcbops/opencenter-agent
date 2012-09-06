#!/usr/bin/env python

import sys
from bashscriptrunner import BashScriptRunner

name = "Chef"
script = BashScriptRunner(script_path=["plugins/lib/%s" % name])
 

def setup(config):
    LOG.debug('Doing setup in test.py')
    register_action('install_chef', install_chef)


def install_chef(input_data):
    payload = input_data['payload']
    action  = input_data['action']
    required = ["CHEF_SERVER", "CHEF_VALIDATOR"]
    optional = ["CHEF_RUNLIST", "CHEF_ENVIRONMENT", "CHEF_VALIDATION_NAME"]
    env = dict([k,v for k,v in payload if k in required + optional ])
    for r in required:
        if not env.has_key(required):
            return { 'result_code': 22,
             'result_str': 'Bad Request (missing %s)' % r,
             'result_data': None }
    script.run_env("install_chef.sh", env, "")
    return { 'result_code': 0,
             'result_str': 'success',
             'result_data': None }
    #env = {"CHEFSERVER": "
    #script.run_env(

def get_env_from_payload(payload, accept_keys):
    
