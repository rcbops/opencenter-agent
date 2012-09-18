#!/usr/bin/env python

name = 'output'

class State():
    def __init__(self):
        self.output_setup_called = False
        self.output_teardown_called = False
        self.output_handler_called = False

state = State()

def setup(config={}):
    state.output_setup_called = True

# TODO: This isn't currently called
def teardown():
    state.output_teardown_called = True

# This won't get called
def handler(input_data):
    state.output_handler_called = True
