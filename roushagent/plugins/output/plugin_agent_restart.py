#!/usr/bin/env python
#
# Copyright 2012, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
import sys
import time

from roushclient.client import RoushEndpoint

name = 'agent_restart'


def setup(config={}):
    LOG.debug('Setting up restart_agent plugin')
    register_action('agent_restart', restart_agent)


def restart_agent(input_data):
    payload = input_data['payload']
    pid = os.fork()
    if pid != 0:
        # Parent Process
        _respawn()

    else:
        # Child Process
        result = _success()
        task_id = input_data['id']
        endpoint_url = global_config['endpoints']['admin']
        ep = RoushEndpoint(endpoint_url)
        task = ep.tasks[task_id]
        task._request_get()
        task.state = 'done'
        task.result = result
        task.save()


def _return(result_code, result_str, result_data=None):
    if result_data is None:
        result_data = {}
    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': result_data}


def _success(result_str='success', result_data=None):
    if result_data is None:
        result_data = {}
    return _return(0, result_str, result_data)


def _respawn():
    args = sys.argv[:]
    LOG.info('Re-spawning %s' % ' '.join(args))
    args.insert(0, sys.executable)
    os.execv(sys.executable, args)
