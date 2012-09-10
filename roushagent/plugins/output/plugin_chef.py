#!/usr/bin/env python

import sys
import os
from bashscriptrunner import BashScriptRunner

name = "chef"

def setup(config={}):
    LOG.debug('Doing setup in test.py')
    plugin_dir = config.get("plugin_dir", "roushagent/plugins")
    script_path = [os.path.join(plugin_dir, "lib", name)]
    script = BashScriptRunner(script_path=script_path)
    register_action('install_chef', lambda x: install_chef(x, script))
    register_action('run_chef', lambda x: run_chef(x, script))


def install_chef(input_data, script):
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


def run_chef(input_data, script):
    payload = input_data['payload']
    action = input_data['action']
    return script.run("run-chef.sh")
