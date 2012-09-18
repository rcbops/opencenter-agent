#!/usr/bin/env python

name = 'input'

class State():
    def __init__(self):
        self.input_setup_called = False
        self.input_teardown_called = False
        self.input_fetch_called = False

state = State()

def setup(config={}):
    state.input_setup_called = True

def teardown():
    state.input_teardown_called = True

def fetch():
    result = {
        'id': 'test',
        'action': 'test',
        'payload': {}
        }

    state.input_fetch_called = True
    return result
