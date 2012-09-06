#!/usr/bin/env python

def setup():
    LOG.debug('Doing setup in test.py')
    register_action('test', handle_test)

def handle_test(input_data):
    payload = input_data['payload']
    action = input_data['action']

    print 'Handling action "%s" for payload "%s"' % (action, payload)
    return { 'result_code': 0,
             'result_str': 'success',
             'result_data': None }
