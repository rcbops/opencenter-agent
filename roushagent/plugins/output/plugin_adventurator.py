#!/usr/bin/env python

import base64
import logging
import os
import random
import time

from state import StateMachine, StateMachineState
from primitives import OrchestratorTasks

name = 'adventurator'


def setup(config={}):
    LOG.debug('doing setup for sleep handler')
    register_action('adventurate', handle_adventurate)

def handle_adventurate(input_data):
    action = input_data['action']
    payload = input_data['payload']

    if not 'dsl' in payload:
        return _retval(1, friendly_str='no dsl specified in request')

    if not 'node_list' in payload:
        return _retval(1, friendly_str='no node_list specified in request')

    # let the exception bubble up
    ns = {}
    ns['StateMachine'] = StateMachine
    ns['StateMachineState'] = StateMachineState
    ns['OrchestratorTasks'] = OrchestratorTasks()

    ns['LOG'] = LOG

    exec base64.b64decode(payload['dsl']) in ns, ns

    output_data = {'result_code': 1,
                   'result_str': 'no return from adventure',
                   'result_data': {}}

    if 'output_data' in ns:
        output_data = ns['output_data']

    return output_data

def _retval(result_code, friendly_str=None, result_data={}):
    if not friendly_str:
        friendly_str = 'success' if result_code == 0 else 'fail'

    return {'result_code': result_code,
            'result_str': friendly_str,
            'result_data': result_data}
