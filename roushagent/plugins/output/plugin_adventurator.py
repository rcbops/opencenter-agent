#!/usr/bin/env python

import base64
import json
import logging
import os
import random
import time

from state import StateMachine, StateMachineState
from primitives import OrchestratorTasks

name = 'adventurator'


def setup(config={}):
    self.roush_endpoint = 'http://localhost:8080'

    if 'roush_endpoint' in config:
        self.roush_endpoint = config['roush_endpoint']

    LOG.debug('doing setup for %s handler' % name)
    register_action('adventurate', handle_adventurate)

def handle_adventurate(input_data):
    action = input_data['action']
    payload = input_data['payload']

    if not 'dsl' in payload:
        return _retval(1, friendly_str='no dsl specified in request')

    if not 'initial_state' in payload:
        return _retval(1, friendly_str='no initial_state specified in request')

    dsl = base64.b64decode(payload['dsl'])
    # see if this is json or python
    dsl_type = 'python'
    try:
        dsl = json.loads(dsl)
        dsl_type = 'json'
    except Exception as e:
        LOG.debug('apparently not json: %s' % str(e))


    # let the exception bubble up
    ns = {}
    ns['LOG'] = LOG
    ns['StateMachine'] = StateMachine
    ns['StateMachineState'] = StateMachineState
    ns['tasks'] = OrchestratorTasks(endpoint=self.roush_endpoint)
    ns['input_data'] = payload['initial_state']
    ns['result_str'] = 'fail'
    ns['result_code'] = 254
    ns['result_data'] = {}

    if dsl_type == 'json':
        ns['sm_description'] = dsl

    ns['LOG'] = LOG

    if dsl_type == 'json':
        exec '(result_data, _) = tasks.sm_eval(sm_description, input_data)' in ns, ns
    else:
        exec base64.b64decode(dsl) in ns, ns

    output_data = {'result_code': 1,
                   'result_str': 'no return data from adventure',
                   'result_data': {}}

    if 'result_data' in ns:
        output_data = ns['result_data']
    return output_data

def _retval(result_code, friendly_str=None, result_data={}):
    if not friendly_str:
        friendly_str = 'success' if result_code == 0 else 'fail'

    return {'result_code': result_code,
            'result_str': friendly_str,
            'result_data': result_data}
