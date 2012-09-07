#!/usr/bin/env python

import sys
from bashscriptrunner import BashScriptRunner

name = "chef"
script = BashScriptRunner(script_path=["roushagent/plugins/lib/%s" % name])


def setup(config):
    LOG.debug('Doing setup in test.py')
    register_action('install_chef', install_chef)
    register_action('run_chef', run_chef)


def install_chef(input_data):
    payload = input_data['payload']
    action = input_data['action']
    required = ["CHEF_SERVER", "CHEF_VALIDATOR"]
    optional = ["CHEF_RUNLIST", "CHEF_ENVIRONMENT", "CHEF_VALIDATION_NAME"]
    env = dict([(k, v) for k, v in payload.iteritems()
                if k in required + optional])
    for r in required:
        if not r in env:
            return {'result_code': 22,
                    'result_str': 'Bad Request (missing %s)' % r,
                    'result_data': None}
    return script.run_env("install-chef.sh", env, "")

def run_chef(input_data):
    payload = input_data['payload']
    action = input_data['action']
    return script.run("run-chef.sh")
