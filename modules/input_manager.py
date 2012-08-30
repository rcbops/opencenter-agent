#!/usr/bin/env python

import os
import logging

LOG = logging.getLogger('input')

# incoming json looks like:
#
# { "command": {
#     "action": "registered_action",
#     "args": []
#     }
# }
#
# input plugins receive the data, and mash it into the
# proper json form, if necessary.  Plugins can thread,
# although input is serialized, and dispatched serially
# through consumer plugins.
#
# each input plugin will have the setup method called,
# and a teardown method on application stop.  the
# fetch() method will return the next json blob available
# to be processed.  In the case of a single plugin,
# the plugin can block, but multiple input plugins with
# blocking fetches() would be bad.
#
# a plugin which does not block can pass back an empty dict,
# which will drop the manager into polling mode.
#

class InputManager:
    def __init__(self, path):
        # Load all available plugins, or those
        # specficied by the config.
        self.input_plugins = {}
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
        ns = { 'LOG': LOG }

        LOG.debug("Loading input plugin file %s" % path)

        # FIXME(rp): Handle exceptions
        execfile(path,ns)

        print "server_thread in loadfile: " + str(dir(ns['server_thread']))

        name = path
        if 'name' in ns:
            name = ns['name']

        self.input_plugins[name] = ns

        if 'setup' in ns:
            ns['setup']()

        print "server_thread after setup in loadfile: " + str(dir(ns['server_thread']))

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


    def fetch(self):
        # walk through all the different input managers and fetch the
        # next input message.
        #
        # there is a possibility of starvation here if one plugin manages
        # to get much more input than the other.  Probably could order the
        # plugins by last valid response or something to keep one plugin
        # from monopolizing the input queue.  In fact, FIXME
        #
        result = {}

        for input_plugin in self.input_plugins:
            if 'fetch' in self.input_plugins[input_plugin]:
                result = self.input_plugins[input_plugin]['fetch']()
                if len(result):
                    return result

        # otherwise, nothing
        return result
