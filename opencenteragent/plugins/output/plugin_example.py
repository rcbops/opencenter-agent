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

name = 'example'


def setup(config={}):
    LOG.debug('Doing setup in test.py')
    register_action('test', handle_test)


def handle_test(input_data):
    payload = input_data['payload']
    action = input_data['action']

    print 'Handling action "%s" for payload "%s"' % (action, payload)
    return {'result_code': 0,
            'result_str': 'success',
            'result_data': None}
