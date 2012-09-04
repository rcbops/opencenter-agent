#!/usr/bin/env python

import os
import sys
import json
import logging
import time

from modules import PluginManager
from modules import InputManager

if __name__ == "__main__":
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler(sys.stderr))

    output_handler = PluginManager(['modules/plugin_files.py'])
    input_handler = InputManager(['modules/task_input.py'])

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
                log.debug('Data: %s' % result['data'])

                out = {'result_code': 255,
                       'result_str': 'unknown error',
                       'result_data': ''}

                try:
                    out = output_handler.dispatch(result['data']['action'],
                                                  result['data']['payload'])
                except Exception as e:
                    out = { 'result_code': 254,
                            'result_str': 'dispatch error',
                            'result_data': str(e) }

                input_handler.result(result, out)

    except KeyboardInterrupt:
        pass

    input_handler.stop()
