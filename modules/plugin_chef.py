#!/usr/bin/env python

def setup():
    LOG.debug('Doing setup in plugin_chef.py')
    register_action('test', handle_test)

def handle_test(payload):
    print 'Handling test action for payload %s' % payload

    return [ 0, 'success', {} ]

def install_chef(payload):
    try:
        server = payload['chef']['server']
        env = payload['chef']['environment']
    except KeyError, e:
        LOG.error("Required attribute %s not received for install_chef" % 
                  e.args[0])
        return [ 1, 'missing argument', {"argument": e.args[0]}]


