#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################
#

import base64
import json
import logging
import os
import random
import time

from opencenteragent.utils import detailed_exception
from opencenterclient.client import OpenCenterEndpoint
from state import StateMachine, StateMachineState
from primitives import OrchestratorTasks

name = 'adventurator'
endpoint = 'http://localhost:8080/admin'


def setup(config={}):
    global endpoint
    endpoint = 'http://localhost:8080/admin'

    if 'admin' in global_config.get('endpoints', {}):
        endpoint = global_config['endpoints']['admin']

    LOG.debug('doing setup for %s handler' % name)
    register_action('adventurate', handle_adventurate)


def handle_adventurate(input_data):
    global endpoint

    parent_id = input_data['id']
    action = input_data['action']
    payload = input_data['payload']

    adventure_dsl = None
    adventure_id = None

    ep = OpenCenterEndpoint(endpoint)

    if 'adventure' in payload:
        adventure_obj = ep.adventures[int(payload['adventure'])]
        adventure_dsl = adventure_obj.dsl
        adventure_id = payload['adventure']
    elif 'adventure_dsl' in payload:
        adventure_dsl = payload['adventure_dsl']
        adventure_id = 0

    if not adventure_dsl:
        return _retval(1,
                       friendly_str='must specify adventure or adventure_dsl')

    if not 'nodes' in payload:
        return _retval(1, friendly_str='no "nodes" list in request')

    if 'initial_state' in payload:
        initial_state = payload['initial_state']
    else:
        initial_state = {}

    if not 'nodes' in initial_state:
        initial_state['nodes'] = payload['nodes']

    adv_globals = []
    if 'globals' in payload:
        adv_globals = payload['globals']

    LOG.debug('using globals %s' % adv_globals)

    ns = {}
    ns['LOG'] = LOG
    ns['StateMachine'] = StateMachine
    ns['StateMachineState'] = StateMachineState
    ns['tasks'] = OrchestratorTasks(endpoint=endpoint,
                                    parent_task_id=parent_id,
                                    adventure_globals=adv_globals)
    ns['input_data'] = initial_state
    ns['result_str'] = 'fail'
    ns['result_code'] = 254
    ns['result_data'] = {}
    ns['sm_description'] = adventure_dsl

    LOG.debug('About to run the following dsl: %s' % adventure_dsl)

    node_list = {}

    ns['input_data']['fails'] = []

    for node in initial_state['nodes']:
        node_list[int(node)] = 'ok'
        attr_obj = ep.attrs.new()
        attr_obj.node_id = node
        attr_obj.key = 'last_task'
        attr_obj.value = 'ok'
        attr_obj.save()

    try:
        exec '(result_data, state_data) = ' \
            'tasks.sm_eval(sm_description, input_data)' in ns, ns
    except Exception as e:
        for node in node_list.keys():
            attr_obj = ep.attrs.new()
            attr_obj.node_id = node
            attr_obj.key = 'last_task'
            attr_obj.value = 'failed'
            attr_obj.save()

        return _retval(1, result_data=detailed_exception())

    output_data = {'result_code': 1,
                   'result_str': 'no return data from adventure',
                   'result_data': {}}

    if 'result_data' in ns:
        output_data = ns['result_data']

    history = []

    if 'state_data' in ns and \
            'history' in ns['state_data']:
        history = ns['state_data']['history']

    # clean up any failed tasks.
    LOG.debug('Adventure terminated with state: %s' % ns['state_data'])

    rollbacks = {}

    # walk through the history and assemble a rollback plan
    for entry in history:
        # walk through the history and assemble rollback plans
        for k, v in entry['result_data'].items():
            k = int(k)
            if not k in rollbacks:
                rollbacks[k] = []
            if 'rollback' in v['result_data'] and \
                    len(v['result_data']['rollback']) > 0:
                if isinstance(v['result_data']['rollback'], list):
                    rollbacks[k] += v['result_data']['rollback']
                else:
                    rollbacks[k].append(v['result_data']['rollback'])
                # v['result_data'].pop('history')

    state_data = ns['state_data']
    output_data['result_data']['history'] = history

    output_data['result_data']['rollbacks'] = rollbacks

    if 'fails' in state_data:
        # we need to walk through all the failed nodes.
        for node in map(lambda x: int(x), state_data['fails']):
            node_list[node] = 'failed'
            if node in rollbacks and len(rollbacks[node]) > 0:
                LOG.debug('Running rollback plan for node %d: %s' %
                          (node, rollbacks[node]))

                ns['sm_description'] = rollbacks[node]
                ns['input_data'] = {'nodes': [node]}

                try:
                    exec '(rollback_result, rollback_state) = tasks.sm_eval(' \
                        'sm_description, input_data)' in ns, ns

                    if 'rollback_result' in ns and \
                            'result_code' in ns['rollback_result']:
                        if ns['rollback_result']['result_code'] == 0:
                            node_list[node] = 'rollback'
                        else:
                            LOG.debug('Error in rollback: %s: %s' %
                                      (ns['rollback_result'],
                                       ns['rollback_state']))

                except Exception as e:
                    LOG.debug('Exception running rollback: %s\n%s' %
                              (str(e), detailed_exception()))
            else:
                LOG.debug('No rollback plan for failed node %d' % node)

    for node in node_list.keys():
        attr_obj = ep.attrs.new()
        attr_obj.node_id = int(node)
        attr_obj.key = 'last_task'
        attr_obj.value = node_list[node]
        attr_obj.save()

    return output_data


def _retval(result_code, friendly_str=None, result_data={}):
    if not friendly_str:
        friendly_str = 'success' if result_code == 0 else 'fail'

    return {'result_code': result_code,
            'result_str': friendly_str,
            'result_data': result_data}
