#!/usr/bin/env python

import os
import logging

LOG = logging.getLogger('output')

# output modules recieve an input action, and return an output
# result.  Generally they take the form of actions to perform.
#
# output plugins *must* export a "name" value.  In addition,
# they *must* export a "setup" function, which takes a config hash.
# The config hash will be merely the config items in the section
# of the main configfile named the same as the "name" value exported
# by the plugin.
#
# when the setup function is called, it should register actions
# that it is willing to handle.  It can use the "register_action()"
# function exported into the module namespace to do so.
#
# other items injected into module namespace:
#
# LOG - a python logging handler
# global_config - the global config hash
# module_config - the configuration for the module
# register_action()
#
# after registering an action, any incoming data sent to
# a specific action will be sent to the registered dispatch
# handler, as registered by the module.
#
# The dispatch functions will receive a python dict with two items:
#
# "id": a unique transaction id (generated by the input module)
# "action": the action that that caused the dispatch to be called
# "payload": the input dict recieved from the input module
#
# The payload is arbitrary, and is specific to the action.
#
# The dispatch handler should processes the message, and return
# a python dict in the following format:
#
# {
#   'result_code': <result-code-ish>
#   'result_str': <error-or-success-message>
#   'result_data': <extended error info or arbitrary data> }
#


class OutputManager:
    def __init__(self, path, config={}):
        # Load all available plugins, or those
        # specified by the config.
        self.output_plugins = {}

        # should all actions be named module.action?
        self.loaded_modules = ['modules']
        self.dispatch_table = {'modules.list': [self.handle_modules],
                               'modules.load': [self.handle_modules],
                               'modules.reload': [self.handle_modules]}
        self.config = config
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
        ns = {'register_action': self.register_action,
              'global_config': self.config,
              'LOG': LOG}

        LOG.debug('Loading plugin file %s' % path)

        # FIXME(rp): Handle exceptions
        execfile(path, ns)

        if not 'name' in ns:
            raise ImportError('Plugin missing "name" value')

        name = ns['name']
        self.loaded_modules.append(name)
        self.output_plugins[name] = ns
        config = self.config.get(name, {})

        ns['module_config'] = config

        if 'setup' in ns:
            ns['setup'](config)
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

    def dispatch(self, input_data):
        # look at the dispatch table for matching actions
        # and dispatch them in order to the registered
        # handlers.
        #
        # Not sure what exactly to do with multiple
        # registrations for the same event, so we'll
        # punt and just pass to the first successful.
        #
        action = input_data['action']

        result = {'result_code': 253,
                  'result_str': 'no dispatcher',
                  'result_data': ''}

        if action in self.dispatch_table:
            LOG.debug('plugin_manager: dispatching action %s' % action)
            for fn in self.dispatch_table[action]:
                # FIXME(rp): handle exeptions
                result = fn(input_data)
                LOG.debug('Got result %s' % result)
                if 'result_code' in result and result['result_code'] == 0:
                    return result

        else:
            LOG.warning('No dispatch for action "%s"' % action)

        return result

    # some internal methods to provide some agent introspection
    def handle_modules(self, input_data):
        action = input_data['action']
        payload = input_data['payload']

        result_code = 1
        result_str = 'failed to perform action'
        result_data = ''

        if action == 'modules.list':
            result_code = 0
            result_str = 'success'
            result_data = self.loaded_modules
        elif action == 'modules.load':
            if not 'path' in payload:
                result_str = 'no "path" specified in payload'
            elif not os.path.isfile(payload['path']):
                result_str = 'specified module does not exist'
            else:
                # any exceptions we'll bubble up from the manager
                self.loadfile(payload['path'])

        elif action == 'modules.reload':
            pass

        return {'result_code': result_code,
                'result_str': result_str,
                'result_data': result_data}

    def stop(self):
        for plugin in self.output_plugins:
            if 'teardown' in self.output_plugins[plugin]:
                self.output_plugins[plugin]['teardown']()
