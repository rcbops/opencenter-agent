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

    output_handler = PluginManager(['modules/plugin_example.py'])
    input_handler = InputManager(['modules/input_example.py'])

    # we'll assume non-blocking.  we should negotiate this
    # with the plugins, I suppose
    do_quit = False

    try:
        while not do_quit:
            result = input_handler.fetch()
            if len(result) == 0:
                time.sleep(5)
            else:
                output_handler.dispatch('test', result)
    except KeyboardInterrupt:
        pass

    input_handler.stop()
