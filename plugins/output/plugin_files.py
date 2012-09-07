#!/usr/bin/env python

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
