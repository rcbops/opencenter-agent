#!/usr/bin/env python

import getopt
import json
import logging
import os
import socket
import sys
import time

from ConfigParser import ConfigParser

from modules import OutputManager
from modules import InputManager

def daemonize():
    if os.fork():
        sys.exit(0)
    else:
        os.setsid()
        os.chdir('/')
        os.umask(0)
        if os.fork():
            sys.exit(0)

if __name__ == '__main__':
    daemonize = False
    debug = False
    configfile = None
    config = {"main": {}}

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:vd')
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(1)

    for o, a in opts:
        if o == '-c':
            configfile = a
        elif o == '-v':
            debug = True
        elif o == '-d':
            daemonize = True
        else:
            usage()
            sys.exit(1)

    log = logging.getLogger()
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.WARNING)

    if daemonize:
        log.addHandler(logging.SysLogHandler(address='/var/log'))
        daemonize()
    else:
        log.addHandler(logging.StreamHandler(sys.stderr))

    if configfile:
        cp = ConfigParser()
        cp.read(configfile)
        config = dict([[s, dict(cp.items(s))] for s in cp.sections()])

    # get directory/path layout
    base_dir = config['main'].get('base_dir', os.path.dirname(__file__))
    plugin_dir = config['main'].get('plugin_dir', os.path.join(base_dir, 'plugins'))
    sys.path.append(os.path.join(plugin_dir, 'lib'))

    # find input and output handlers to load
    output_handlers = config['main'].get('output_handlers', 'plugins/output/plugin_files.py')
    input_handlers = config['main'].get('input_handlers', 'plugins/input/task_input.py')

    output_handler = OutputManager(
        [ x.strip() for x in output_handlers.split(',')], config)
    input_handler = InputManager(
        [ x.strip() for x in input_handlers.split(',')], config)

    # we'll assume non-blocking.  we should negotiate this
    # with the plugins, I suppose
    do_quit = False

    try:
        while not do_quit:
            result = input_handler.fetch()
            if len(result) == 0:
                time.sleep(5)
            else:
                log.debug('Got input from input handler "%s"' %
                          result['plugin'])
                log.debug('Data: %s' % result['input'])

                result['output'] = {'result_code': 255,
                                    'result_str': 'unknown error',
                                    'result_data': ''}

                try:
                    result['output'] = output_handler.dispatch(result['input'])

                except Exception as e:
                    result['output'] = { 'result_code': 254,
                                         'result_str': 'dispatch error',
                                         'result_data': str(e) }

                input_handler.result(result)

    except KeyboardInterrupt:
        pass

    input_handler.stop()
