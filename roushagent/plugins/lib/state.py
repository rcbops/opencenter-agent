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

import copy
import logging
import time


class StateMachine:
    def __init__(self, state_data={}, logger=None):
        self.states = {'success': StateMachineState(
            terminal=True,
            advance=lambda x: self._return(
                {'result_code': 0,
                 'result_str': 'adventure ran',
                 'result_data': {}}, x)),
            'failure': StateMachineState(
                terminal=True,
                advance=lambda x: self._return(
                    {'result_code': 1,
                     'result_str': 'adventure failed',
                     'result_data': {}}, x))}
        self.current_state = 'success'
        self.state_data = state_data
        self.result = True

        if not 'history' in self.state_data:
            self.state_data['history'] = []

        self.logger = logger
        if not logger:
            self.logger = logging.getLogger()

    def _return(self, result, state):
        return (result, state)

    def set_state(self, state):
        self.current_state = state

    def add_state(self, name, state):
        if state in self.states:
            raise ValueError('state %s already exists' % name)

        self.states[name] = state

    # this is a bit odd... it returns true if the state machine can continue,
    # or false otherwise
    def advance(self):
        if not self.current_state in self.states.keys():
            raise ValueError('no state "%s" in state machine' % state)

        self.logger.debug('Running state %s' % self.current_state)

        # run and go
        self.result, self.state_data = self.states[self.current_state].advance(
            self.state_data)

        if self.states[self.current_state].terminal:
            return False

        # keep the old result data in history...
        self.state_data['history'].insert(0, copy.deepcopy(self.result))

        # we've run out of nodes to act on... we've filtered out all of the
        # nodes, or else we've had task failures on individual nodes such
        # that none of them are remaining.
        if len(self.state_data['nodes']) == 0:
            self.current_state = self.states[self.current_state].on_failure

        if self.states[self.current_state].sleep:
            time.sleep(self.states[self.current_state].sleep)

        if self.result['result_code'] == 0:
            self.current_state = self.states[self.current_state].on_success
        else:
            self.current_state = self.states[self.current_state].on_failure

        self.logger.debug('Advanced state to %s as result of outcome %s' % (
            self.current_state, self.result))

        return True

    def run_to_completion(self):
        while self.advance():
            pass

        return (self.result, self.state_data)


class StateMachineState:
    def __init__(self, **kwargs):
        self.params = {'on_success': 'success',
                       'on_failure': 'failure',
                       'sleep': 0,
                       'advance': self.not_implemented,
                       'terminal': False}
        self.params.update(kwargs)

    def not_implemented(self, state):
        return (False, {})

    def __getattr__(self, name):
        if not name in self.params.keys():
            raise AttributeError

        return self.params[name]
