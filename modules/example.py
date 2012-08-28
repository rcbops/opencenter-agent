#!/usr/bin/env python

def setup():
    LOG.debug('Doing setup in test.py')
    register_action('test', handle_test)

def handle_test(payload):
    print 'Handling test action for payload %s' % payload

    return [ 0, 'success', {} ]
