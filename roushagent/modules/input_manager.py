#!/usr/bin/env python

import os
import logging

LOG = logging.getLogger('input')

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


class InputManager:
    def __init__(self, path, config={}):
        # Load all available plugins, or those
        # specficied by the config.
        self.input_plugins = {}
        self.config = config
        self.load(path)

    def _load_directory(self, path):
        dirlist = os.listdir(path)
        for relpath in dirlist:
            p = os.path.join(path, relpath)

            if not os.path.isdir(p) and p.endswith(".py"):
                self._load_file(p)

    def _load_file(self, path):
        # we can't really load this into the existing namespace --
        # we'll have registration collisions.
        ns = {'LOG': LOG}

        LOG.debug("Loading input plugin file %s" % path)

        # FIXME(rp): Handle exceptions
        execfile(path, ns)

        if not 'name' in ns:
            raise ImportError('Plugin missing name value')

        name = ns['name']

        self.input_plugins[name] = ns

        config = self.config.get(name, {})

        if 'setup' in ns:
            ns['setup'](config)

    def load(self, path):
        # Load a plugin by file name.  modules with
        # action_foo methods will be auto-registered
        # for the "foo" action
        if type(path) == list:
            for d in path:
                self.load(d)
        else:
            if os.path.isdir(path):
                self._load_directory(path)
            else:
                self._load_file(path)

    def stop(self):
        # run 'teardown' on all the loaded modules
        for input_plugin in self.input_plugins:
            if 'teardown' in self.input_plugins[input_plugin]:
                self.input_plugins[input_plugin]['teardown']()

    def result(self, result):
        input_data = result['input']
        output_data = result['output']
        plugin = result['plugin']

        if 'result' in self.input_plugins[plugin]:
            LOG.debug('sending result outcome to plugin "%s"' % plugin)
            self.input_plugins[plugin]['result'](input_data, output_data)

    def fetch(self):
        # walk through all the different input managers and fetch the
        # next input message.
        #
        # there is a possibility of starvation here if one plugin manages
        # to get much more input than the other.  Probably could order the
        # plugins by last valid response or something to keep one plugin
        # from monopolizing the input queue.  In fact, FIXME
        #
        for input_plugin in self.input_plugins:
            if 'fetch' in self.input_plugins[input_plugin]:
                fetch_result = self.input_plugins[input_plugin]['fetch']()
                if len(fetch_result):
                    return {"plugin": self.input_plugins[input_plugin]['name'],
                            "input": fetch_result}

        # otherwise, nothing
        return {}
