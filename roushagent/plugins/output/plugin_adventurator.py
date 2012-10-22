#!/usr/bin/env python

import base64
import json
import logging
import os
import random
import time

from roushclient.client import RoushEndpoint
from state import StateMachine, StateMachineState
from primitives import OrchestratorTasks

name = 'adventurator'
roush_endpoint = 'http://localhost:8080'

def setup(config={}):
    global roush_endpoint
    roush_endpoint = 'http://localhost:8080'

    if 'roush_endpoint' in config:
        roush_endpoint = config['roush_endpoint']

    LOG.debug('doing setup for %s handler' % name)
    register_action('adventurate', handle_adventurate)

def handle_adventurate(input_data):
    global roush_endpoint

    action = input_data['action']
    payload = input_data['payload']

    if not 'adventure' in payload:
        return _retval(1, friendly_str='no adventure specified in request')

    if not 'nodes' in payload:
        return _retval(1, friendly_str='no "nodes" list in request')

    ep = RoushEndpoint(roush_endpoint)

    adventure = payload['adventure']
    if 'initial_state' in payload:
        initial_state = payload['initial_state']
    else:
        initial_state = {}

    if not 'nodes' in initial_state:
        initial_state['nodes'] = payload['nodes']

    adventure_obj = ep.adventures[int(adventure)]

    ns = {}
    ns['LOG'] = LOG
    ns['StateMachine'] = StateMachine
    ns['StateMachineState'] = StateMachineState
    ns['tasks'] = OrchestratorTasks(endpoint=roush_endpoint)
    ns['input_data'] = initial_state
    ns['result_str'] = 'fail'
    ns['result_code'] = 254
    ns['result_data'] = {}
    ns['sm_description'] = adventure_obj.dsl

    LOG.debug('About to run the following dsl: %s' % adventure_obj.dsl)
    exec '(result_data, state_data) = tasks.sm_eval(sm_description, input_data)' in ns, ns

    output_data = {'result_code': 1,
                   'result_str': 'no return data from adventure',
                   'result_data': {}}

    if 'result_data' in ns:
        output_data = ns['result_data']

    if 'state_data' in ns:
        output_data['result_data']['history'] = ns['state_data']['history']

    # clean up any failed tasks.
    LOG.debug('Adventure terminated with state: %s' % ns['state_data'])

    state_data = ns['state_data']

    if 'fails' in state_data:
        # we need to walk through all the failed nodes.
        for node in map(lambda x: int(x), state_data['fails']):
            if 'rollback_plan' in state_data and node in state_data['rollback_plan']:

                LOG.debug('Running rollback plan for node %d' % node)
                ns['sm_description'] = state_data['rollback_plan'][node]
                ns['input_data'] = { 'nodes': [node] }

                exec 'tasks.sm_eval(sm_description, input_data)' in ns, ns
            else:
                LOG.debug('No rollback plan for failed node %d' % node)

    return output_data

def _retval(result_code, friendly_str=None, result_data={}):
    if not friendly_str:
        friendly_str = 'success' if result_code == 0 else 'fail'

    return {'result_code': result_code,
            'result_str': friendly_str,
            'result_data': result_data}
