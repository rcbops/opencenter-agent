#!/usr/bin/env python

import base64
import json
import logging
import os
import random
import time

from roushagent.utils import detailed_exception
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

    parent_id = input_data['id']
    action = input_data['action']
    payload = input_data['payload']

    adventure_dsl = None
    adventure_id = None

    ep = RoushEndpoint(roush_endpoint)

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
    ns['tasks'] = OrchestratorTasks(endpoint=roush_endpoint,
                                    parent_task_id=parent_id,
                                    adventure_globals=adv_globals)
    ns['input_data'] = initial_state
    ns['result_str'] = 'fail'
    ns['result_code'] = 254
    ns['result_data'] = {}
    ns['sm_description'] = adventure_dsl

    LOG.debug('About to run the following dsl: %s' % adventure_dsl)

    node_list = []
    # let's mark all the nodes as running adventure...
    for node in initial_state['nodes']:
        node_list.append(node)
        node_obj = ep.nodes[node]
        node_obj.adventure_id = adventure_id
        node_obj.save()

    try:
        exec '(result_data, state_data) = ' \
            'tasks.sm_eval(sm_description, input_data)' in ns, ns
    except Exception as e:
        for node in node_list:
            node_obj._request_get()
            node_obj.adventure_id = None
            node_obj.save()

        return _retval(1, result_data=detailed_exception(e))

    output_data = {'result_code': 1,
                   'result_str': 'no return data from adventure',
                   'result_data': {}}

    if 'result_data' in ns:
        output_data = ns['result_data']

    if 'state_data' in ns and \
            'history' in ns['state_data']:
        output_data['result_data']['history'] = ns['state_data']['history']

    # clean up any failed tasks.
    LOG.debug('Adventure terminated with state: %s' % ns['state_data'])

    state_data = ns['state_data']

    if 'fails' in state_data:
        # we need to walk through all the failed nodes.
        for node in map(lambda x: int(x), state_data['fails']):
            if 'rollback_plan' in state_data and (
                    node in state_data['rollback_plan']):

                LOG.debug('Running rollback plan for node %d' % node)
                ns['sm_description'] = state_data['rollback_plan'][node]
                ns['input_data'] = {'nodes': [node]}

                try:
                    exec 'tasks.sm_eval(sm_description, input_data)' in ns, ns
                except Exception as e:
                    pass
            else:
                LOG.debug('No rollback plan for failed node %d' % node)

    for node in node_list:
        node_obj = ep.nodes[node]
        # force a refresh - need to set up partial puts
        node_obj._request_get()
        node_obj.adventure_id = None
        node_obj.save()

    return output_data


def _retval(result_code, friendly_str=None, result_data={}):
    if not friendly_str:
        friendly_str = 'success' if result_code == 0 else 'fail'

    return {'result_code': result_code,
            'result_str': friendly_str,
            'result_data': result_data}
