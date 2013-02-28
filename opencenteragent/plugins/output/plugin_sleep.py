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
#

import os
import random
import time

name = 'sleep'


def setup(config={}):
    LOG.debug('doing setup for sleep handler')
    register_action('sleep', handle_sleep,
                    args={"sleep_interval": {"required": True, "type": "int"}})


def handle_sleep(input_data):
    action = input_data['action']
    payload = input_data['payload']

    sleep_time = int(payload.get('sleep_interval', 5))
    success_percentage = payload.get('success_percentage', 100)

    result = random.randrange(1, 100)

    result_code = 1
    if result <= success_percentage:
        result_code = 0

    time.sleep(sleep_time)

    result_str = ['success!', 'fail!'][result_code]
    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': {'sleep_interval': sleep_time,
                            'success_percentage': success_percentage,
                            'random': result}}
