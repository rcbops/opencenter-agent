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
# 

import os

name = 'files'


def setup(config={}):
    LOG.debug('doing setup for files handler')
    register_action('files_list', handle_files)
    register_action('files_get', handle_files)


def handle_files(input_data):
    action = input_data['action']
    payload = input_data['payload']

    result_code = 1
    result_str = 'no file specified'
    result_data = ''

    if action == 'files_list':
        path = '/'

        if 'path' in payload:
            path = payload['path']

        try:
            result_data = os.listdir(path)
            result_code = 0
            result_str = 'success'

        except Exception as e:
            result_code = 1
            result_str = str(e)
            result_data = ''  # could be full backtrace

    elif action == 'files_get':

        if 'file' in payload:
            try:
                with open(payload['file'], 'r') as f:
                    result_data = f.read()
                    result_code = 0
                    result_str = 'success'
            except Exception as e:
                result_code = 1
                result_str = str(e)
                result_data = ''  # could be full backtrace

    return {'result_code': result_code,
            'result_str': result_str,
            'result_data': result_data}
