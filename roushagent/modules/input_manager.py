#!/usr/bin/env python
# 
# Copyright 2012, Rackspace US, Inc. 
# 
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
# 
#     http://www.apache.org/licenses/LICENSE-2.0 
# 
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 
# 

import os
import logging

import manager

LOG = logging.getLogger('roush.input')

# Input modules export a number of functions and attributes:
#
# name = <string>
# setup()                       # optional
# teardown()                    # optional
# fetch(blocking=False)         # blocking optional (see below)
# result(transaction, result)   # optional
#
# the "name" attribute is an optional "friendly name" for
# logging purposes.  Default name is derived from file name.
#
# The "setup" function performs whatever initialization is required
# for the module, including such things as background threads
# if necessary for the input module.  Once the setup function is
# called, subsequent calls to the fetch() function should return
# task data as specified below.
#
# Likewise, the "teardown" function performs any necessary cleanup
# and shutdown of the module.  It must return, as shutdown requests
# to the daemon call each input module's teardown functions in series.
#
# The "input" function fetches task data from whatever source is
# appropriate and returns a python dict in this form:
#
# { 'id': ...,            # some unique id for the command
#   'action': '...',      # output handler dispatcher
#   'payload': '...' }    # arbitrary jsonable data for task dispatcher
#
# Note that these are minimum requirements.  Other keys may be
# specified for input module bookkeeping, and will be passed back on a
# result() call.
#
# input plugins receive the data, and mash it into the proper dict
# form, if necessary.  Plugins can thread, although input is
# serialized, and dispatched serially through consumer plugins.
#
# each input plugin will have the setup method called, and a teardown
# method on application stop.  the fetch() method will return the next
# dict available to be processed.
#
# The input plugin will be passed a blocking flag.  Input plugins MAY
# implement a blocking fetch(), but are not required to.  They MUST
# implement a non-blocking fetch, however.  If an input plugin is
# asked to perform a blocking fetch, but does not actually have the
# ability to perform a blocking fetch, it should return and empty
# dict, signifying an inability to perform a blocking fetch.  When
# performing a blocking fetch, then, the plugin MAY NOT return an
# empty dict, but must block until a new dict is ready to be consumed.
#
# The optional "result" function receives the original output dict, as
# well as a "result" dict (as returned from the output plugin).  If
# the plugin has a need to update status, it can do so.
#


class InputManager(manager.Manager):
    def __init__(self, path, config={}):
        super(InputManager, self).__init__(path, config=config)
        self.load(path)

    def result(self, result):
        input_data = result['input']
        output_data = result['output']
        plugin = result['plugin']

        if 'result' in self.plugins[plugin]:
            LOG.debug('sending result outcome to plugin "%s"' % plugin)
            self.plugins[plugin]['result'](input_data, output_data)

    def fetch(self):
        # walk through all the different input managers and fetch the
        # next input message.
        #
        # there is a possibility of starvation here if one plugin manages
        # to get much more input than the other.  Probably could order the
        # plugins by last valid response or something to keep one plugin
        # from monopolizing the input queue.  In fact, FIXME
        #
        for input_plugin in self.plugins:
            if 'fetch' in self.plugins[input_plugin]:
                fetch_result = self.plugins[input_plugin]['fetch']()
                if len(fetch_result):
                    return {"plugin": self.plugins[input_plugin]['name'],
                            "input": fetch_result}

        # otherwise, nothing
        return {}
