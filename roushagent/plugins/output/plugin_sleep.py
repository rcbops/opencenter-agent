#!/usr/bin/env python

import os
import random
import time

name = 'sleep'


def setup(config={}):
    LOG.debug('doing setup for sleep handler')
    register_action('sleep', handle_sleep, args={"sleep_interval": {
                "required": True, "type": "int"}}
)


def handle_sleep(input_data):
    action = input_data['action']
    payload = input_data['payload']

    sleep_time = payload.get('time', 5)
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
