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
    chef = ChefThing(script, config)
    register_action('install_chef', chef.install_chef)
    register_action('run_chef', chef.run_chef)


class ChefThing(object):
    def __init__(self, script, config):
        self.script = script
        self.config = config
        
    def install_chef(self, input_data):
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
        return self.script.run_env("install-chef.sh", env, "")

    def run_chef(self, input_data):
        payload = input_data['payload']
        action = input_data['action']
        return self.script.run("run-chef.sh")
