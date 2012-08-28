#!/usr/bin/env python

import os
import logging

LOG = logging.getLogger('plugins')


# incoming json looks like:
#
# { "command": {
#     "action": "registered_action",
#     "args": []
#     }
# }
#
# Each plugin must register its own actions.  Multiply registered
# actions will all receive notification for the event.
#
# Return values are json, looking like:
#
# { "response": {
#     "result_code": <result-code-ish>
#     "result_str": <error-or-success-message>
#     "result_err": <extended error info (backtrace, stderr, etc)
#   }
# }

class PluginManager:
    def __init__(self, path):
        # Load all available plugins, or those
        # specficied by the config.
        self.dispatch_table = {}
        LOG.debug("Loading plugins from %s" % path)
        self.load(path)
        LOG.debug('Dispatch table: %s' % self.dispatch_table)

    def _load_directory(self, path):
        dirlist = os.listdir(path)
        for relpath in dirlist:
            p = os.path.join(path, relpath)

            if not os.path.isdir(p) and p.endswith(".py"):
                self._load_file(p)

    def _load_file(self, path):
        # we can't really load this into the existing namespace --
        # we'll have registration collisions.

        # we could prepopulate callback functions here, if
        # we had any..
        LOG.debug("Loading plugin file %s" % path)

        ns = { 'register_action': self.register_action,
               'LOG': LOG }

        execfile(path,ns)

        if 'setup' in ns:
            ns['setup']()
        else:
            LOG.warning('No setup function in %s.  Ignoring.' % path)

    def register_action(self, action, method):
        LOG.debug('registering handler for action %s' % action)

        if action in self.dispatch_table:
            self.dispatch_table[action].append(method)
        else:
            self.dispatch_table[action] = [method]

    def load(self, path):
        # Load a plugin by file name.  modules with
        # action_foo methods will be auto-registered
        # for the "foo" action
        if os.path.isdir(path):
            self._load_directory(path)
        else:
            self._load_file(path)

    def dispatch(self, action, payload):
        # look at the dispatch table for matching actions
        # and dispatch them in order to the registered
        # handlers.
        # if action in self.dispatch_table:
        #     for fn in self.dispatch_table[action]:

        pass
