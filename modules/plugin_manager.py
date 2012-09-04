#!/usr/bin/env python

import os
import logging


LOG = logging.getLogger('plugins')

# incoming data is the action and an arbitrary dict.
#
# Each plugin must register its own actions.  Multiply registered
# actions will all receive notification for the event.
#
# Return values are dicts, looking like:
#
# { 'response': {
#     'result_code': <result-code-ish>
#     'result_str': <error-or-success-message>
#     'result_data': <extended error info or arbitrary data>
#   }
# }

class PluginManager:
    def __init__(self, path):
        # Load all available plugins, or those
        # specficied by the config.
        self.dispatch_table = {}
        self.load(path)

        LOG.debug('Dispatch table: %s' % self.dispatch_table)

    def _load_directory(self, path):
        dirlist = os.listdir(path)
        for relpath in dirlist:
            p = os.path.join(path, relpath)

            if not os.path.isdir(p) and p.endswith('.py'):
                self._load_file(p)

    def _load_file(self, path):
        # we can't really load this into the existing namespace --
        # we'll have registration collisions.
        ns = { 'register_action': self.register_action,
               'LOG': LOG }

        LOG.debug('Loading plugin file %s' % path)

        # FIXME(rp): Handle exceptions
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
        # for the 'foo' action
        if type(path) == list:
            for d in path:
                self.load(d)
        else:
            if os.path.isdir(path):
                self._load_directory(path)
            else:
                self._load_file(path)

    def dispatch(self, action, payload):
        # look at the dispatch table for matching actions
        # and dispatch them in order to the registered
        # handlers.
        result = {'result_code': 253,
                  'result_str': 'no dispatcher',
                  'result_data': '' }

        if action in self.dispatch_table:
            LOG.debug('plugin_manager: dispatching action %s' % action)
            for fn in self.dispatch_table[action]:
                # FIXME(rp): handle exeptions
                result = fn(action, payload)
                LOG.debug('Got result %s' % result)
                if 'result_code' in result and result['result_code'] == 0:
                    return result

            LOG.warning('plugin_manager: could not successfully dispatch')
            return result
        else:
            LOG.warning('No dispatch for action "%s"' % action)
