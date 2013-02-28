#!/usr/bin/env python
#               OpenCenter(TM) is Copyright 2013 by Rackspace US, Inc.
##############################################################################
#
# OpenCenter is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  This
# version of OpenCenter includes Rackspace trademarks and logos, and in
# accordance with Section 6 of the License, the provision of commercial
# support services in conjunction with a version of OpenCenter which includes
# Rackspace trademarks and logos is prohibited.  OpenCenter source code and
# details are available at: # https://github.com/rcbops/opencenter or upon
# written request.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 and a copy, including this
# notice, is available in the LICENSE file accompanying this software.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the # specific language governing permissions and limitations
# under the License.
#
##############################################################################

name = 'output'


class State():
    def __init__(self):
        self.output_setup_called = False
        self.output_teardown_called = False
        self.output_handler_called = False

state = State()


def setup(config={}):
    state.output_setup_called = True
    register_action('test', handler)


# TODO: This isn't currently called
def teardown():
    state.output_teardown_called = True


def handler(input_data):
    state.output_handler_called = True
    payload = input_data['payload']
    action = input_data['action']

    return {'result_code': 0,
            'result_str': 'success',
            'result_data': None}
