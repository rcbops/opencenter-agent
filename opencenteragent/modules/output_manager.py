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

import os
import logging
import socket
import select
import time
from functools import partial

import manager

LOG = logging.getLogger('opencenter.output')

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


def _ok(code=0, message='success', data={}):
    return {'result_code': code,
            'result_str': message,
            'result_data': data}


def _fail(code=1, message='unknown failure', data={}):
    return _ok(code, message, data)


def _xfer_to_eof(fd_in, sock_out):
    while True:
        bytes_read = fd_in.read(1024)
        if len(bytes_read) == 0:
            # fd_in EOF.
            return True

        try:
            bytes_sent = sock_out.send(bytes_read)
        except:
            return False

        if bytes_sent == 0:
            # remote socket shut down
            return False


class OutputManager(manager.Manager):
    def __init__(self, path, config={}):
        super(OutputManager, self).__init__(path, config=config)

        # should all actions be named module.action?
        self.dispatch_table = {}
        self.register_action('modules', 'modules', 'logfile.tail',
                             self.handle_logfile)
        self.register_action('modules', 'modules', 'logfile.watch',
                             self.handle_logfile)
        self.register_action('modules', 'modules', 'modules.list',
                             self.handle_modules)
        self.register_action('modules', 'modules', 'modules.load',
                             self.handle_modules)
        self.register_action('modules', 'modules', 'modules.actions',
                             self.handle_modules)
        self.register_action('modules', 'modules', 'modules.reload',
                             self.handle_modules)

        self.load(path)

        LOG.debug('Dispatch methods: %s' % self.dispatch_table.keys())

    def register_action(self, plugin, shortpath, action, method,
                        constraints=[], consequences=[], args={},
                        timeout=30):
        LOG.debug('Registering handler for action %s' % action)
        # First handler wins
        if action in self.dispatch_table:
            action_details = self.dispatch_table[action]
            raise NameError('Action %s already registered to %s:%s'
                            % (action, action_details['short_path'],
                               action_details['method']))
        else:
            self.dispatch_table[action] = {'method': method,
                                           'shortpath': shortpath,
                                           'function': method.func_name,
                                           'plugin': plugin,
                                           'constraints': constraints,
                                           'consequences': consequences,
                                           'arguments': args,
                                           'timeout': timeout}

    def actions(self):
        d = {}
        for action, params in self.dispatch_table.items():
            d[action] = {'plugin': params['plugin'],
                         'constraints': params['constraints'],
                         'consequences': params['consequences'],
                         'args': params['arguments'],
                         'timeout': params['timeout']}
        return d

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
                  'result_str': 'no dispatcher found for action "%s"' % action,
                  'result_data': ''}
        if action in self.dispatch_table:
            # TODO(mikal): we don't really need the locals here
            params = self.dispatch_table[action]
            fn = params['method']
            path = params['shortpath']
            plugin = params['plugin']

            LOG.debug('Plugin_manager: dispatching action %s from plugin %s' %
                      (action, plugin))
            LOG.debug('Received input_data %s' % (input_data))
            base = self.config['main'].get('trans_log_dir',
                                           '/var/log/opencenter')

            if not os.path.isdir(base):
                raise OSError(2, 'Specified path "%s" ' % (base) +
                              'does not exist or is not a directory.')

            if not os.access(base, os.W_OK):
                raise OSError(13,
                              'Specified path "%s" is not writable.' %
                              base)

            # we won't log from built-in functions
            ns = None
            if plugin in self.plugins:
                ns = self.plugins[plugin]
                t_LOG = ns['LOG']
                if 'id' in input_data:
                    ns['LOG'] = logging.getLogger(
                        'opencenter.output.trans_%s' % input_data['id'])
                    h = logging.FileHandler(os.path.join(base, 'trans_%s.log' %
                                                         input_data['id']))
                    ns['LOG'].addHandler(h)

            # FIXME(rp): handle exceptions
            result = fn(input_data)

            if ns is not None:
                ns['LOG'] = t_LOG

            LOG.debug('Got result %s' % result)
        else:
            if action.startswith('rollback_'):
                result = {'result_code': 0,
                          'result_str': 'no rollback action for %s' % action,
                          'result_data': {}}
            else:
                LOG.warning('No dispatch for action "%s"' % action)
        return result

    # some internal methods to provide some agent introspection
    def handle_logfile(self, input_data, sock=None):
        """Handle logfile reading.

        :param: input_data: dictionary of inputs to the handler
        :param: sock:       a socket. Only set this if you're a unit test.

        :returns: a result dictionary
        """

        offset = 0

        action = input_data['action']
        payload = input_data.get('payload', {})
        timeout = payload.get('timeout', 0)

        if not 'task_id' in payload or \
                not 'dest_ip' in payload or \
                not 'dest_port' in payload:
            return _fail(message='must specify task_id, '
                         'dest_ip and dest_port')

        base = self.config['main'].get('trans_log_dir', '/var/log/opencenter')
        log_path = os.path.join(base, 'trans_%s.log' % payload['task_id'])

        if not os.path.exists(log_path):
            return _fail(message='no such transaction log file')

        data = ''
        fd = open(log_path, 'r')
        fd.seek(0, os.SEEK_END)
        length = fd.tell()

        if action == 'logfile.tail':
            offset = max(length - 1024, 0)

        fd.seek(offset)

        # open the socket and jet it out
        if not sock:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            try:
                sock.connect((payload['dest_ip'],
                              int(payload['dest_port'])))
            except socket.error as e:
                fd.close()
                sock.close()
                return _fail(message='%s' % str(e))

            result = _xfer_to_eof(fd, sock)
            if timeout == 0:
                fd.close()
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()

            if result is False:
                return _fail(code=1, message='remote socket disconnect')

            if timeout == 0:
                return _ok()

            # we're polling to end of file.  Socket and fd are open,
            # fd is at EOF.  Wait for file size to change
            pos = fd.tell()
            remaining_timeout = timeout

            while remaining_timeout > 0:
                time.sleep(1)
                remaining_timeout -= 1

                # would be nice to be able to detect remote socket
                # disconnected.  Sadly this doesn't seem trivially
                # doable.
                fd.seek(0, os.SEEK_END)
                if fd.tell() != pos:
                    # new data in file
                    fd.seek(pos, os.SEEK_SET)
                    result = _xfer_to_eof(fd, sock)
                    if not result:
                        return _fail(message='remote socket disconnect')

                    pos = fd.tell()
                    remaining_timeout = timeout

        finally:
            try:
                # This will fail if the socket isn't open
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            sock.close()

        return _ok()

    def handle_modules(self, input_data):
        action = input_data['action']
        payload = input_data.get('payload')

        if action == 'modules.list':
            return _ok(data={'name': 'opencenter_agent_output_modules',
                             'value': self.loaded_modules})
        elif action == 'modules.actions':
            return _ok(data={'name': 'opencenter_agent_actions',
                             'value': self.actions()})
        elif action == 'modules.load':
            if not payload:
                return _fail(message='no payload specified')
            if not 'path' in payload:
                return _fail(message='no "path" specified in payload')
            if not os.path.isfile(payload['path']):
                return _fail(message='specified module does not exist')

            # any exceptions we'll bubble up from the manager
            self.loadfile(payload['path'])
        elif action == 'modules.reload':
            pass
        return _ok()
